import cv2
import numpy as np
import base64
import json
import os
import shutil
import asyncio
import traceback
from fastapi import FastAPI, WebSocket, UploadFile, File, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

# Import our modules
from backend.modules.vehicle_detection import VehicleDetector
from backend.modules.vehicle_tracking import VehicleTracker
from backend.modules.speed_estimation import SpeedEstimator
from backend.modules.noise_filtering import TrajectorySmoother
from backend.modules.behavior_analysis import BehaviorAnalyzer
from backend.modules.risk_prediction import RiskPredictor
from backend.modules.benchmarking import PerformanceMonitor
from backend.modules.accident_detection import AccidentDetector
from backend.modules.violations_db import (
    init_db,
    add_violation, upsert_violation, get_all_violations, get_violations_by_vehicle,
    delete_violation, delete_all_violations,
    add_accident, get_all_accidents, delete_accident, delete_all_accidents,
)

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- Initialize Global Models ---
print("[System] Loading global AI model (YOLO)...")
global_detector = VehicleDetector()

# --- Initialize database on startup ---
@app.on_event("startup")
async def startup_event():
    init_db()
    print("[API] Violations database initialized.")


# ─────────────────────────────────────────────────────────────────────────────
# REST API — File Upload
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_location = UPLOAD_DIR / file.filename
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "message": "Upload successful"}


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Violations CRUD
# ─────────────────────────────────────────────────────────────────────────────

class ViolationCreate(BaseModel):
    video_name: str
    tracker_vehicle_id: int
    vehicle_unique_id: str
    vehicle_type: str = "Unknown"
    plate_number: Optional[str] = None
    plate_image: Optional[str] = None
    detected_speed: float
    speed_limit: float
    area: Optional[str] = "Unknown"
    frame_image: Optional[str] = None
    violation_type: Optional[str] = "Overspeed"
    status: Optional[str] = "reported"


@app.get("/api/violations")
async def api_get_all_violations():
    """Fetch all stored violations (newest first)."""
    return get_all_violations()


@app.get("/api/violations/{vehicle_unique_id}")
async def api_get_violations_by_vehicle(vehicle_unique_id: str):
    """Fetch violations for a specific globally unique vehicle ID."""
    records = get_violations_by_vehicle(vehicle_unique_id)
    if not records:
        return []
    return records


@app.post("/api/violations")
async def api_create_violation(body: ViolationCreate):
    """Manually insert a violation record."""
    record = add_violation(
        video_name=body.video_name,
        tracker_vehicle_id=body.tracker_vehicle_id,
        vehicle_unique_id=body.vehicle_unique_id,
        vehicle_type=body.vehicle_type,
        plate_number=body.plate_number,
        plate_image=body.plate_image,
        detected_speed=body.detected_speed,
        speed_limit=body.speed_limit,
        area=body.area or "Unknown",
        frame_image=body.frame_image,
        violation_type=body.violation_type or "Overspeed",
        status=body.status or "reported",
    )
    return record


@app.delete("/api/violations/{violation_id}")
async def api_delete_violation(violation_id: int):
    """Delete a violation record by ID."""
    deleted = delete_violation(violation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"message": "Violation deleted", "id": violation_id}


@app.delete("/api/violations")
async def api_clear_all_violations():
    """Delete all violation records."""
    count = delete_all_violations()
    return {"message": f"Successfully deleted {count} violations.", "deleted_count": count}


# ─────────────────────────────────────────────────────────────────────────────
# REST API — Accidents CRUD
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/accidents")
async def api_get_all_accidents():
    """Fetch all stored accident records (newest first)."""
    return get_all_accidents()


@app.delete("/api/accidents/{accident_id}")
async def api_delete_accident(accident_id: int):
    """Delete an accident record by ID."""
    deleted = delete_accident(accident_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Accident not found")
    return {"message": "Accident deleted", "id": accident_id}


@app.delete("/api/accidents")
async def api_clear_all_accidents():
    """Delete all accident records."""
    count = delete_all_accidents()
    return {"message": f"Successfully deleted {count} accident records.", "deleted_count": count}

# ─────────────────────────────────────────────────────────────────────────────
# WebSocket — Real-time Video Processing
# ─────────────────────────────────────────────────────────────────────────────

def _get_area_label(speed_limit: float) -> str:
    """Return a human-readable area name for a given speed limit."""
    area_map = {
        30: "School Zone",
        50: "City",
        60: "Suburban",
        80: "Highway",
        100: "Expressway",
        120: "Motorway",
    }
    return area_map.get(int(speed_limit), f"Custom ({int(speed_limit)} km/h)")


def _crop_vehicle_frame(frame: np.ndarray, bbox: list) -> str:
    """
    Crop the vehicle bounding box from the frame and encode as Base64 JPEG.
    Returns empty string on failure.
    """
    try:
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""
        _, buffer = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return ""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

    try:
        # Initialize modules per connection
        detector = global_detector
        tracker = VehicleTracker()
        speed_estimator = SpeedEstimator()
        smoother = TrajectorySmoother()
        behavior_analyzer = BehaviorAnalyzer()
        risk_predictor = RiskPredictor()
        monitor = PerformanceMonitor()
        accident_detector = AccidentDetector()
        # Violation deduplication: vehicle_id -> max speed recorded
        violation_max_speeds: dict[int, float] = {}
        # Per-track histories for accident detection
        speed_histories: dict[int, list] = {}
        position_histories: dict[int, list] = {}

        while True:
            # Wait for start command with filename
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("command") == "start":
                filename = message.get("filename")
                try:
                    speed_limit = float(message.get("speed_limit", 50))
                except (ValueError, TypeError):
                    speed_limit = 50.0

                area_label = _get_area_label(speed_limit)
                print(f"Starting processing: {filename} with speed limit: {speed_limit} km/h")

                file_path = UPLOAD_DIR / filename

                if not file_path.exists():
                    await websocket.send_json({"error": "File not found"})
                    continue

                cap = cv2.VideoCapture(str(file_path))
                fps_video = cap.get(cv2.CAP_PROP_FPS)
                if not fps_video:
                    fps_video = 30
                speed_estimator.fps = fps_video

                monitor.start_frame()

                if not cap.isOpened():
                    print(f"Error: Could not open video source {file_path}")
                    await websocket.send_json({"error": f"Could not open video file: {filename}"})
                    cap.release()
                    continue

                # Reset tracking state for new video session
                violation_max_speeds.clear()
                speed_histories.clear()
                position_histories.clear()
                accident_detector.collision_frames.clear()

                try:
                    import time
                    frame_count = 0
                    while cap.isOpened():
                        try:
                            track_data = []
                            alerts = []
                            saved_violations = []  # all violations saved this frame

                            ret, frame = cap.read()
                            if not ret:
                                if frame_count == 0:
                                    print("Error: Video has no frames")
                                    await websocket.send_json({"error": "Video file is empty or unreadable"})
                                else:
                                    print("Video processing complete")
                                    await websocket.send_json({"status": "complete"})
                                break

                            frame_count += 1

                            # ── Detection & Tracking Pipeline ──────────────────
                            detections = detector.detect_frame(frame)
                            tracks = tracker.update_tracks(detections, frame)

                            # ── DEBUG: every 30 frames print pipeline status ───
                            if frame_count % 30 == 0:
                                print(f"[DEBUG] Frame {frame_count}: {len(detections)} detections, {len(tracks)} confirmed tracks, speed_limit={speed_limit}")

                            current_time = time.time()

                            # ── Build per-session history dicts ───────────────
                            # (Used by AccidentDetector; capped to last 30 entries)
                            MAX_HIST = 30

                            for track in tracks:
                                track_id = track.track_id
                                ltrb = track.to_ltrb()
                                x1, y1, x2, y2 = map(int, ltrb)
                                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                                
                                # Extract vehicle type from DeepSORT track
                                vehicle_type = getattr(track, 'det_class', None)
                                if vehicle_type is None and hasattr(track, 'get_det_class'):
                                    vehicle_type = track.get_det_class()
                                if not vehicle_type:
                                    vehicle_type = "Unknown"

                                sx, sy = smoother.smooth(track_id, cx, cy)
                                speed = speed_estimator.estimate_speed(track_id, sx, sy)

                                if speed is None:
                                    speed = 0.0

                                # Update speed / position history for accident detection
                                spd_hist = speed_histories.setdefault(track_id, [])
                                pos_hist = position_histories.setdefault(track_id, [])
                                spd_hist.append(speed)
                                pos_hist.append((sx, sy))
                                if len(spd_hist) > MAX_HIST:
                                    spd_hist.pop(0)
                                    pos_hist.pop(0)

                                # ── DEBUG: log speed every 30 frames per track ──
                                if frame_count % 30 == 0:
                                    print(f"[DEBUG]   Track {track_id} ({vehicle_type}): speed={speed:.1f} km/h, limit={speed_limit}, violation={speed > speed_limit}")

                                flags = behavior_analyzer.analyze(track_id, speed, (sx, sy))
                                risk = risk_predictor.calculate_risk(flags)

                                violation = bool(speed > speed_limit)

                                track_info = {
                                    "id": int(track_id),
                                    "type": vehicle_type,
                                    "speed": float(round(speed, 1)),
                                    "speed_limit": float(speed_limit),
                                    "violation": violation,
                                    "risk": float(round(risk, 2)),
                                    "flags": list(flags),
                                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                                }
                                track_data.append(track_info)

                                # ── Violation alert text ───────────────────────
                                if violation:
                                    alerts.append(
                                        f"Vehicle {track_id}: Speed violation ({int(speed)} km/h > {speed_limit} km/h)"
                                    )

                                if flags:
                                    for flag in flags:
                                        alerts.append(f"Vehicle {track_id}: {flag}")

                                # ── Persistent violation storage ─────────────
                                if violation:
                                    vehicle_unique_id = f"{filename}_{track_id}"
                                    area_key = f"{vehicle_unique_id}_{area_label}"
                                    max_recorded = violation_max_speeds.get(area_key, -1.0)
                                    # Save to DB on first detection OR when speed has increased by >= 2 km/h
                                    if max_recorded < 0 or speed >= max_recorded + 2.0:
                                        # Update max speed in memory
                                        violation_max_speeds[area_key] = speed

                                        # Capture vehicle crop
                                        crop_b64 = _crop_vehicle_frame(frame, [x1, y1, x2, y2])

                                        print(f"[DEBUG] >>> SAVING VIOLATION to DB: vehicle={vehicle_unique_id}, speed={speed:.1f}, limit={speed_limit}")
                                        # Upsert to DB
                                        result = upsert_violation(
                                            video_name=filename,
                                            tracker_vehicle_id=int(track_id),
                                            vehicle_unique_id=vehicle_unique_id,
                                            vehicle_type=vehicle_type,
                                            detected_speed=float(round(speed, 1)),
                                            speed_limit=float(speed_limit),
                                            area=area_label,
                                            frame_image=crop_b64 if crop_b64 else None,
                                        )

                                        if result["action"] in ("inserted", "updated"):
                                            saved_violations.append({
                                                "action": result["action"],
                                                "record": result["record"],
                                            })
                                            print(f"[DB] {result['action'].capitalize()} violation: Vehicle {vehicle_unique_id} at {speed:.1f} km/h")

                                # ── Visualisation ──────────────────────────────
                                color = (0, 255, 0)
                                if 'Overspeeding' in flags:
                                    color = (0, 0, 255)
                                elif flags:
                                    color = (0, 165, 255)

                                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                                label = f"ID:{track_id} {vehicle_type} {int(speed)}km/h"
                                cv2.putText(frame, label, (x1, y1 - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                            # ── Accident Detection (after per-track loop) ──────────────
                            accident_events = accident_detector.detect_accident(
                                tracks, speed_histories, position_histories, frame_count
                            )

                            saved_accidents = []
                            for event in accident_events:
                                # ── Visualise: red overlay on union bbox ─────────
                                ux1, uy1, ux2, uy2 = event.bbox_union
                                h_f, w_f = frame.shape[:2]
                                ux1 = max(0, min(ux1, w_f - 1))
                                uy1 = max(0, min(uy1, h_f - 1))
                                ux2 = max(0, min(ux2, w_f - 1))
                                uy2 = max(0, min(uy2, h_f - 1))

                                # Semi-transparent red fill
                                overlay = frame.copy()
                                cv2.rectangle(overlay, (ux1, uy1), (ux2, uy2), (0, 0, 255), -1)
                                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                                # Solid red border
                                cv2.rectangle(frame, (ux1, uy1), (ux2, uy2), (0, 0, 220), 3)

                                # Red bbox on each involved vehicle
                                for vid in event.vehicle_ids:
                                    vid_track = next((t for t in tracks if t.track_id == vid), None)
                                    if vid_track:
                                        ltrb = vid_track.to_ltrb()
                                        vx1,vy1,vx2,vy2 = map(int, ltrb)
                                        cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (0, 0, 255), 3)
                                        cv2.putText(frame,
                                            f"ID:{vid} ACCIDENT",
                                            (vx1, vy1 - 12),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

                                # Banner text on frame
                                cv2.putText(frame,
                                    f"ACCIDENT: Vehicles {', '.join(map(str, event.vehicle_ids))}",
                                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                                # Capture snapshot AFTER drawing
                                snap_b64 = _crop_vehicle_frame(frame, event.bbox_union)

                                # Save to DB
                                vehicle_ids_str = ",".join(map(str, event.vehicle_ids))
                                signals_str = ",".join(event.signals)
                                rec = add_accident(
                                    vehicle_ids=vehicle_ids_str,
                                    frame_number=frame_count,
                                    area=area_label,
                                    signals=signals_str,
                                    details=event.details,
                                    snapshot=snap_b64 if snap_b64 else None,
                                )
                                saved_accidents.append(rec)
                                print(f"[ACCIDENT] Detected: Vehicles {vehicle_ids_str} | Signals: {signals_str} | Frame {frame_count}")

                            # ── Encode frame ───────────────────────────────────
                            current_fps = monitor.update_fps()
                            _, buffer = cv2.imencode('.jpg', frame)
                            frame_base64 = base64.b64encode(buffer).decode('utf-8')

                            response = {
                                "image": frame_base64,
                                "fps": round(current_fps, 1),
                                "vehicles": track_data,
                                "alerts": alerts,
                            }

                            # Include saved violations so frontend can update live
                            if saved_violations:
                                response["violation_saved"] = True
                                latest = saved_violations[-1]
                                response["violation_action"] = latest["action"]
                                response["new_violation"] = latest["record"]
                                response["saved_violations"] = saved_violations

                            # Include accident events if any
                            if saved_accidents:
                                response["accident_detected"] = True
                                response["accident_event"] = saved_accidents[-1]
                                response["accident_action"] = "inserted"

                            await websocket.send_text(json.dumps(response))

                            # Small sleep to prevent event loop blocking
                            await asyncio.sleep(0.001)

                        except WebSocketDisconnect:
                            print("Client disconnected during stream")
                            break
                        except Exception as e:
                            print(f"[ERROR] Exception in frame {frame_count}: {e}")
                            traceback.print_exc()
                            continue
                finally:
                    cap.release()
                    try:
                        await websocket.send_json({"status": "finished"})
                    except Exception:
                        pass

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
