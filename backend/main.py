import cv2
import numpy as np
import base64
import json
import os
import shutil
import asyncio
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Import our modules (now in backend.modules)
from backend.modules.vehicle_detection import VehicleDetector
from backend.modules.vehicle_tracking import VehicleTracker
from backend.modules.speed_estimation import SpeedEstimator
from backend.modules.noise_filtering import TrajectorySmoother
from backend.modules.behavior_analysis import BehaviorAnalyzer
from backend.modules.risk_prediction import RiskPredictor
from backend.modules.benchmarking import PerformanceMonitor

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

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_location = UPLOAD_DIR / file.filename
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "message": "Upload successful"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

    try:
        # Initialize modules per connection
        detector = VehicleDetector() # Ensure YOLO model is loaded (cached)
        tracker = VehicleTracker()
        speed_estimator = SpeedEstimator()
        smoother = TrajectorySmoother()
        behavior_analyzer = BehaviorAnalyzer()
        risk_predictor = RiskPredictor()
        monitor = PerformanceMonitor()

        while True:
            # Wait for start command with filename
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("command") == "start":
                filename = message.get("filename")
                file_path = UPLOAD_DIR / filename
                
                if not file_path.exists():
                    await websocket.send_json({"error": "File not found"})
                    continue

                cap = cv2.VideoCapture(str(file_path))
                fps_video = cap.get(cv2.CAP_PROP_FPS)
                if not fps_video: fps_video = 30
                speed_estimator.fps = fps_video
                
                monitor.start_frame()
                
                while cap.isOpened():
                    track_data = [] # Data to send to frontend
                    alerts = []
                    
                    ret, frame = cap.read()
                    if not ret:
                        await websocket.send_json({"status": "complete"})
                        break

                    # --- Processing Pipeline ---
                    detections = detector.detect_frame(frame)
                    tracks = tracker.update_tracks(detections, frame)

                    for track in tracks:
                        track_id = track.track_id
                        ltrb = track.to_ltrb()
                        x1, y1, x2, y2 = map(int, ltrb)
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                        
                        sx, sy = smoother.smooth(track_id, cx, cy)
                        speed = speed_estimator.estimate_speed(track_id, sx, sy)
                        flags = behavior_analyzer.analyze(track_id, speed, (sx, sy))
                        risk = risk_predictor.calculate_risk(flags)
                        
                        # Collect data
                        track_info = {
                            "id": track_id,
                            "speed": round(speed, 1),
                            "risk": round(risk, 2),
                            "flags": flags,
                            "bbox": [x1, y1, x2, y2]
                        }
                        track_data.append(track_info)
                        if flags:
                            for flag in flags:
                                alerts.append(f"Vehicle {track_id}: {flag}")

                        # Visualization on server side (optional, but easier)
                        # Let's draw purely on server for the stream
                        color = (0, 255, 0)
                        if 'Overspeeding' in flags: color = (0, 0, 255)
                        elif flags: color = (0, 165, 255)

                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f"ID:{track_id} {int(speed)}km/h"
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # Encode frame
                    current_fps = monitor.update_fps()
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    response = {
                        "image": frame_base64,
                        "fps": round(current_fps, 1),
                        "vehicles": track_data,
                        "alerts": alerts
                    }
                    
                    await websocket.send_text(json.dumps(response))
                    
                    # Control loop speed (simple throttling)
                    # await asyncio.sleep(0.01) 

                    # Check for stop signal (not implemented in this simple loop, 
                    # but could check websocket.receive with timeout)

                cap.release()
                await websocket.send_json({"status": "finished"})

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
