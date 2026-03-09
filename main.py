import cv2
import argparse
import numpy as np
import time

from backend.modules.vehicle_detection import VehicleDetector
from backend.modules.vehicle_tracking import VehicleTracker
from backend.modules.speed_estimation import SpeedEstimator
from backend.modules.noise_filtering import TrajectorySmoother
from backend.modules.behavior_analysis import BehaviorAnalyzer
from backend.modules.risk_prediction import RiskPredictor
from backend.modules.benchmarking import PerformanceMonitor

def main(source, model_path):
    # Initialize modules
    print("Initializing modules...")
    detector = VehicleDetector(model_path=model_path)
    tracker = VehicleTracker()
    speed_estimator = SpeedEstimator()
    smoother = TrajectorySmoother()
    behavior_analyzer = BehaviorAnalyzer()
    risk_predictor = RiskPredictor()
    monitor = PerformanceMonitor()

    # Open video source
    print(f"Opening video source: {source}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or np.isnan(fps):
        fps = 30
    speed_estimator.fps = fps
    
    print(f"Processing started at {fps} FPS...")

    while True:
        monitor.start_frame()
        ret, frame = cap.read()
        if not ret:
            print("End of video stream.")
            break
        
        # Resize for faster processing if needed (optional)
        # frame = cv2.resize(frame, (1280, 720))

        # 1. Detection
        detections = detector.detect_frame(frame)
        
        # 2. Tracking
        tracks = tracker.update_tracks(detections, frame)
        
        for track in tracks:
            track_id = track.track_id
            
            # Get track bounding box (Left, Top, Right, Bottom)
            ltrb = track.to_ltrb() 
            x1, y1, x2, y2 = map(int, ltrb)
            
            # Calculate centroid
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            
            # 3. Smoothing (Kalman Filter)
            sx, sy = smoother.smooth(track_id, cx, cy)
            
            # 4. Speed Estimation (using smoothed coordinates)
            speed = speed_estimator.estimate_speed(track_id, sx, sy)
            
            # 5. Behavior Analysis
            flags = behavior_analyzer.analyze(track_id, speed, (sx, sy))
            
            # 6. Risk Prediction
            risk = risk_predictor.calculate_risk(flags)
            
            # --- Visualization ---
            color = (0, 255, 0) # Green by default
            if 'Overspeeding' in flags: 
                color = (0, 0, 255) # Red
            elif 'Zig-Zag' in flags or 'Sudden Braking' in flags: 
                color = (0, 165, 255) # Orange
                
            # Draw Bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw Labels
            label_top = f"ID: {track_id}"
            label_bottom = f"{int(speed)} km/h | Risk: {risk:.1f}"
            
            cv2.putText(frame, label_top, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.putText(frame, label_bottom, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw Flags
            if flags:
                flag_str = " | ".join(flags)
                cv2.putText(frame, flag_str, (x1, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Draw FPS
        current_fps = monitor.update_fps()
        cv2.putText(frame, f"FPS: {current_fps:.2f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display
        cv2.imshow("Intelligent Vehicle Monitoring System", frame)
        
        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    monitor.log_performance()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Intelligent Vehicle Monitoring System")
    parser.add_argument('--source', type=str, default='data/test_video.mp4', help='Path to video file or camera index (e.g., 0)')
    parser.add_argument('--model', type=str, default='yolov8n.pt', help='Path to YOLOv8 model file')
    
    args = parser.parse_args()
    
    # Handle numeric source for webcam
    source_input = args.source
    if source_input.isdigit():
        source_input = int(source_input)
        
    main(source_input, args.model)
