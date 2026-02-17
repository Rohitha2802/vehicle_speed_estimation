import cv2
from ultralytics import YOLO
import numpy as np

class VehicleDetector:
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        """
        Initialize the Vehicle Detector using YOLOv8.
        
        Args:
            model_path (str): Path to the YOLOv8 model file.
            confidence_threshold (float): Minimum confidence score for detection.
        """
        print(f"Loading YOLOv8 model from {model_path}...")
        self.model = YOLO(model_path)
        self.conf_threshold = confidence_threshold
        # COCO class IDs for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
        self.vehicle_classes = [2, 3, 5, 7]
        self.class_names = self.model.names

    def detect_frame(self, frame):
        """
        Detect vehicles in a single frame.

        Args:
            frame (numpy.ndarray): Input image frame.

        Returns:
            list: List of detections in format [[x1, y1, x2, y2, score, class_id], ...]
        """
        results = self.model(frame, stream=True, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls_id in self.vehicle_classes and conf >= self.conf_threshold:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detections.append([x1, y1, x2, y2, conf, cls_id])
        
        return detections

    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes on the frame.

        Args:
            frame (numpy.ndarray): Input frame.
            detections (list): List of detections.

        Returns:
            numpy.ndarray: Frame with bounding boxes drawn.
        """
        for x1, y1, x2, y2, conf, cls_id in detections:
            label = f"{self.class_names[cls_id]} {conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame
