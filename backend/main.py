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
from typing import Optional
import sys
from pathlib import Path

# Add the parent directory (project root) to sys.path so 'backend.modules...' works
# even when uvicorn is run from inside the 'backend' folder
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import our modules
from backend.modules.vehicle_detection import VehicleDetector
from backend.modules.vehicle_tracking import VehicleTracker
from backend.modules.speed_estimation import SpeedEstimator
from backend.modules.noise_filtering import TrajectorySmoother
from backend.modules.behavior_analysis import BehaviorAnalyzer
from backend.modules.risk_prediction import RiskPredictor
from backend.modules.benchmarking import PerformanceMonitor
from backend.modules.violations_db import (
    init_db,
    add_violation, upsert_violation, get_all_violations, get_violations_by_vehicle,
    delete_violation, delete_all_violations,
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

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
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
        # Violation deduplication: vehicle_id -> max speed recorded
        violation_max_speeds: dict[int, float] = {}
        # Track IDs to frequency of detected classes to smooth out YOLO misclassifications
        vehicle_types_cache: dict[int, dict[str, int]] = {}
        # Track IDs to set of string flags they have already alerted for to prevent spam
        sent_alerts_cache: dict[int, set[str]] = {}

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
                tracker = VehicleTracker()
                violation_max_speeds.clear()
                vehicle_types_cache.clear()
                sent_alerts_cache.clear()

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
                                current_class = getattr(track, 'det_class', None)
                                if current_class is None and hasattr(track, 'get_det_class'):
                                    current_class = track.get_det_class()
                                    
                                if current_class and current_class != "Unknown":
                                    track_id_int = int(track_id)
                                    if track_id_int not in vehicle_types_cache:
                                        vehicle_types_cache[track_id_int] = {}
                                    vehicle_types_cache[track_id_int][current_class] = vehicle_types_cache[track_id_int].get(current_class, 0) + 1
                                    
                                track_id_int = int(track_id)
                                if track_id_int in vehicle_types_cache:
                                    counts = vehicle_types_cache[track_id_int]
                                    vehicle_type = max(counts, key=counts.get)
                                else:
                                    vehicle_type = "Unknown"

                                sx, sy = smoother.smooth(track_id, cx, cy)
                                speed = speed_estimator.estimate_speed(track_id, sx, sy)

                                if speed is None:
                                    speed = 0.0

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

                                # ── Violation alert text (Spam Suppressed) ─────
                                track_id_int = int(track_id)
                                if track_id_int not in sent_alerts_cache:
                                    sent_alerts_cache[track_id_int] = set()

                                if violation and "Overspeed" not in sent_alerts_cache[track_id_int]:
                                    alerts.append(f"Vehicle {track_id}: Speed violation ({int(speed)} km/h > {speed_limit} km/h)")
                                    sent_alerts_cache[track_id_int].add("Overspeed")

                                if flags:
                                    for flag in flags:
                                        if flag not in sent_alerts_cache[track_id_int]:
                                            alerts.append(f"Vehicle {track_id}: {flag}")
                                            sent_alerts_cache[track_id_int].add(flag)

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
