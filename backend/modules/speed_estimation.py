import numpy as np
import cv2

class SpeedEstimator:
    def __init__(self, pixel_per_meter=10.0, fps=30):
        """
        Initialize the Speed Estimator.

        Args:
            pixel_per_meter (float): Approximation of dynamic pixels per meter.
                                     Ideally this should be calibrated or dynamic.
            fps (int): Frames per second of the video.
        """
        self.ppm = pixel_per_meter
        self.fps = fps
        # track_id -> (timestamp, (cx, cy))
        self.previous_positions = {}
        self.speeds = {}  # track_id -> speed_kmh

    def estimate_speed(self, track_id, center_x, center_y):
        """
        Estimate speed for a given track ID based on pixel displacement.

        Args:
            track_id (int): Unique ID of the vehicle.
            center_x (int): Current X centroid.
            center_y (int): Current Y centroid.

        Returns:
            float: Speed in km/h.
        """
        current_pos = np.array([center_x, center_y])
        
        if track_id in self.previous_positions:
            prev_pos = self.previous_positions[track_id]
            
            # Distance in pixels
            distance_pixels = np.linalg.norm(current_pos - prev_pos)
            
            # Distance in meters
            distance_meters = distance_pixels / self.ppm
            
            # Speed in m/s (assuming 1 frame elapsed)
            # To be more precise, we could store frame indices.
            # Here we assume this function is called every frame.
            speed_ms = distance_meters * self.fps
            
            # Speed in km/h
            speed_kmh = speed_ms * 3.6
            
            # Simple smoothing (optional, but good for display)
            # speed_kmh = 0.9 * self.speeds.get(track_id, 0) + 0.1 * speed_kmh
            self.speeds[track_id] = speed_kmh
        
        self.previous_positions[track_id] = current_pos
        return self.speeds.get(track_id, 0.0)

    def draw_speed(self, frame, track_id, bbox):
        """
        Draw speed on the frame.
        """
        x1, y1, x2, y2 = map(int, bbox)
        speed = self.speeds.get(track_id, 0.0)
        label = f"{int(speed)} km/h"
        cv2.putText(frame, label, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return frame
