import cv2
import numpy as np
import os
from modules.vehicle_detection import VehicleDetector
from modules.vehicle_tracking import VehicleTracker
from modules.speed_estimation import SpeedEstimator
from modules.noise_filtering import TrajectorySmoother
from modules.behavior_analysis import BehaviorAnalyzer
from modules.risk_prediction import RiskPredictor

def test_system():
    print("Testing system modules...")
    
    # Create dummy frame
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    try:
        # Initialize modules
        detector = VehicleDetector()  # Will download yolov8n.pt if not present
        tracker = VehicleTracker()
        speed_estimator = SpeedEstimator()
        smoother = TrajectorySmoother()
        behavior_analyzer = BehaviorAnalyzer()
        risk_predictor = RiskPredictor()
        
        print("Modules initialized successfully.")
        
        # Simulate detection
        # Create a fake car at (100, 100) -> (200, 200)
        detections = detector.detect_frame(frame) # Should be empty
        print(f"Empty detected: {len(detections)}")
        
        # Simulate tracking update with fake data
        fake_detections = [[100, 100, 200, 200, 0.9, 2]] # car
        tracks = tracker.update_tracks(fake_detections, frame)
        print(f"Tracks updated: {len(tracks)}")
        
        print("System verification passed!")

    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_system()
