"""
Accident Detection Module

Detects probable vehicle accidents in real-time from tracked bounding boxes,
speed histories, and position histories.  Three independent signals are
evaluated every frame:

  1. Collision   — IOU overlap between two bboxes exceeds threshold for N frames
  2. Sudden Stop — vehicle speed drops > SUDDEN_STOP_DELTA km/h within a window
  3. Direction   — vehicle heading angle changes > DIRECTION_DELTA_DEG degrees

An **AccidentEvent** is raised when:
  - At least one of the vehicles in a pair has a Sudden Stop OR Direction signal AND
  - The pair also shows a Collision signal for the required number of frames.
  (i.e., collision + 1 more signal = probable accident)

A 10-second per-pair cooldown prevents the same incident flooding alerts.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─── Tuneable constants ────────────────────────────────────────────────────────
IOU_THRESHOLD        = 0.05   # minimum overlap fraction to count as collision
COLLISION_MIN_FRAMES = 3      # consecutive overlap frames needed
SUDDEN_STOP_DELTA    = 20.0   # km/h drop within speed window
SUDDEN_STOP_WINDOW   = 5      # frames to look back for speed drop
DIRECTION_DELTA_DEG  = 60.0   # degrees of heading change = abrupt
DIRECTION_WINDOW     = 5      # frames to look back for direction check
PAIR_COOLDOWN_SEC    = 10.0   # seconds before the same pair can re-alert


# ─── Data class for an accident event ─────────────────────────────────────────
@dataclass
class AccidentEvent:
    vehicle_ids: List[int]           # IDs of involved vehicles
    bbox_union: List[int]            # [x1,y1,x2,y2] union of their bboxes
    signals: List[str]               # e.g. ['Collision', 'Sudden Stop']
    frame_count: int                 # frame number when event fired
    details: str = ""                # human-readable description


# ─── Main detector class ───────────────────────────────────────────────────────
class AccidentDetector:
    def __init__(self):
        # collision_frames[(id_a, id_b)] -> consecutive overlap frame count
        self.collision_frames: Dict[Tuple[int,int], int] = {}
        # last alert time per pair key
        self._last_alert: Dict[str, float] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def detect_accident(
        self,
        tracks,
        speed_histories: Dict[int, List[float]],
        position_histories: Dict[int, List[Tuple[float, float]]],
        frame_count: int = 0,
    ) -> List[AccidentEvent]:
        """
        Evaluate all signals for the current frame and return a list of
        AccidentEvent objects for each newly-confirmed accident.

        Args:
            tracks:              Confirmed DeepSORT track objects (must have
                                 .track_id and .to_ltrb() methods).
            speed_histories:     {track_id: [speed_kmh, ...]} (newest last)
            position_histories:  {track_id: [(cx,cy), ...]}   (newest last)
            frame_count:         Current frame index.

        Returns:
            List[AccidentEvent]  — empty list when no accident detected.
        """
        if len(tracks) < 2:
            self._decay_collision_counts(tracks)
            return []

        # Build bbox map from live tracks
        bbox_map: Dict[int, List[int]] = {}
        for t in tracks:
            ltrb = t.to_ltrb()
            bbox_map[t.track_id] = [int(ltrb[0]), int(ltrb[1]),
                                    int(ltrb[2]), int(ltrb[3])]

        active_ids = set(bbox_map.keys())

        # Prune collision counters for tracks no longer present
        stale = [k for k in self.collision_frames if k[0] not in active_ids or k[1] not in active_ids]
        for k in stale:
            del self.collision_frames[k]

        events: List[AccidentEvent] = []

        # Evaluate every unique pair
        track_ids = sorted(bbox_map.keys())
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                id_a, id_b = track_ids[i], track_ids[j]
                pair_key = f"{id_a}_{id_b}"

                # ── 1. Collision signal ──────────────────────────────────────
                iou = self._compute_iou(bbox_map[id_a], bbox_map[id_b])
                if iou >= IOU_THRESHOLD:
                    self.collision_frames[(id_a, id_b)] = (
                        self.collision_frames.get((id_a, id_b), 0) + 1
                    )
                else:
                    self.collision_frames[(id_a, id_b)] = 0

                collision_confirmed = (
                    self.collision_frames.get((id_a, id_b), 0) >= COLLISION_MIN_FRAMES
                )

                # ── 2. Sudden stop signal (either vehicle) ───────────────────
                sudden_stop_a = self._detect_sudden_stop(id_a, speed_histories)
                sudden_stop_b = self._detect_sudden_stop(id_b, speed_histories)
                sudden_stop   = sudden_stop_a or sudden_stop_b

                # ── 3. Abrupt direction change (either vehicle) ──────────────
                direction_a = self._detect_direction_change(id_a, position_histories)
                direction_b = self._detect_direction_change(id_b, position_histories)
                direction   = direction_a or direction_b

                # ── Combine: need collision + at least one other signal ───────
                extra_signals = []
                if sudden_stop:
                    extra_signals.append("Sudden Stop")
                if direction:
                    extra_signals.append("Abrupt Direction Change")

                if not (collision_confirmed and extra_signals):
                    continue

                # ── Cooldown check ───────────────────────────────────────────
                now = time.time()
                if now - self._last_alert.get(pair_key, 0) < PAIR_COOLDOWN_SEC:
                    continue

                self._last_alert[pair_key] = now

                signals = ["Collision"] + extra_signals
                union_bbox = self._union_bbox(bbox_map[id_a], bbox_map[id_b])
                detail_parts = [f"Collision between Vehicle {id_a} and Vehicle {id_b}"]
                if sudden_stop:
                    detail_parts.append("sudden deceleration detected")
                if direction:
                    detail_parts.append("abrupt direction change detected")

                events.append(AccidentEvent(
                    vehicle_ids=[id_a, id_b],
                    bbox_union=union_bbox,
                    signals=signals,
                    frame_count=frame_count,
                    details="; ".join(detail_parts),
                ))

        return events

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_iou(bbox_a: List[int], bbox_b: List[int]) -> float:
        """Compute Intersection-over-Union for two [x1,y1,x2,y2] boxes."""
        x1 = max(bbox_a[0], bbox_b[0])
        y1 = max(bbox_a[1], bbox_b[1])
        x2 = min(bbox_a[2], bbox_b[2])
        y2 = min(bbox_a[3], bbox_b[3])

        inter_w = max(0, x2 - x1)
        inter_h = max(0, y2 - y1)
        inter   = inter_w * inter_h
        if inter == 0:
            return 0.0

        area_a = max(0, bbox_a[2]-bbox_a[0]) * max(0, bbox_a[3]-bbox_a[1])
        area_b = max(0, bbox_b[2]-bbox_b[0]) * max(0, bbox_b[3]-bbox_b[1])
        union  = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    @staticmethod
    def _detect_sudden_stop(
        track_id: int,
        speed_histories: Dict[int, List[float]],
    ) -> bool:
        """Return True if the vehicle dropped >= SUDDEN_STOP_DELTA km/h
        within the last SUDDEN_STOP_WINDOW frames."""
        hist = speed_histories.get(track_id, [])
        if len(hist) < 2:
            return False
        window = hist[-SUDDEN_STOP_WINDOW:]
        drop = max(window) - min(window[-1], window[-1])
        # Compare earliest vs current within the window
        peak  = max(window[:-1]) if len(window) > 1 else window[0]
        current = window[-1]
        return (peak - current) >= SUDDEN_STOP_DELTA

    @staticmethod
    def _detect_direction_change(
        track_id: int,
        position_histories: Dict[int, List[Tuple[float, float]]],
    ) -> bool:
        """Return True if the vehicle changed heading by >= DIRECTION_DELTA_DEG
        between the previous and current motion vectors."""
        hist = position_histories.get(track_id, [])
        if len(hist) < DIRECTION_WINDOW + 1:
            return False

        def angle(p1, p2):
            dx, dy = p2[0]-p1[0], p2[1]-p1[1]
            return math.degrees(math.atan2(dy, dx))

        window = hist[-(DIRECTION_WINDOW + 1):]
        # Compute heading at mid-point vs current
        mid   = len(window) // 2
        angle_prev    = angle(window[0], window[mid])
        angle_current = angle(window[mid], window[-1])
        delta = abs(angle_current - angle_prev)
        if delta > 180:
            delta = 360 - delta
        return delta >= DIRECTION_DELTA_DEG

    @staticmethod
    def _union_bbox(bbox_a: List[int], bbox_b: List[int]) -> List[int]:
        return [
            min(bbox_a[0], bbox_b[0]),
            min(bbox_a[1], bbox_b[1]),
            max(bbox_a[2], bbox_b[2]),
            max(bbox_a[3], bbox_b[3]),
        ]

    def _decay_collision_counts(self, tracks) -> None:
        """When fewer than 2 tracks exist, reset all collision counters."""
        active = {t.track_id for t in tracks}
        stale = [k for k in self.collision_frames
                 if k[0] not in active or k[1] not in active]
        for k in stale:
            del self.collision_frames[k]
