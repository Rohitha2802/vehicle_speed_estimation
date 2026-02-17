import numpy as np

class BehaviorAnalyzer:
    def __init__(self, speed_limit=80, lateral_threshold=20, braking_threshold=-15):
        """
        Initialize Behavior Analyzer.

        Args:
            speed_limit (float): Speed limit in km/h.
            lateral_threshold (float): Threshold for lateral variance (Zig-Zag).
            braking_threshold (float): Threshold for deceleration (km/h per frame/sec).
        """
        self.speed_limit = speed_limit
        self.lateral_threshold = lateral_threshold
        self.braking_threshold = braking_threshold  # Negative value for deceleration
        self.track_histories = {}  # track_id -> list of (x, y)
        self.speed_histories = {}  # track_id -> list of speeds

    def analyze(self, track_id, speed, position):
        """
        Analyze behavior for a vehicle.

        Args:
            track_id (int): Vehicle ID.
            speed (float): Current speed km/h.
            position (tuple): (x, y) centroid.

        Returns:
            list: List of detected flags ['Overspeeding', 'Zig-Zag', 'Sudden Braking']
        """
        flags = []
        
        # 1. Overspeeding
        if speed > self.speed_limit:
            flags.append('Overspeeding')

        # Update histories
        if track_id not in self.track_histories:
            self.track_histories[track_id] = []
            self.speed_histories[track_id] = []
        
        self.track_histories[track_id].append(position)
        self.speed_histories[track_id].append(speed)
        
        # Keep history short (e.g., last 30 frames)
        if len(self.track_histories[track_id]) > 30:
            self.track_histories[track_id].pop(0)
            self.speed_histories[track_id].pop(0)
            
        history = self.track_histories[track_id]
        
        # 2. Zig-Zag (High lateral variance)
        # Assuming main movement is vertical (Y-axis), check X-axis variance
        if len(history) > 10:
            x_coords = [p[0] for p in history]
            x_variance = np.std(x_coords)
            if x_variance > self.lateral_threshold:
                flags.append('Zig-Zag')

        # 3. Sudden Braking
        if len(self.speed_histories[track_id]) > 2:
            prev_speed = self.speed_histories[track_id][-2]
            acceleration = speed - prev_speed  # Change in speed per frame
            # Use braking_threshold (e.g., -10 km/h per frame interval is huge, adjust based on fps)
            # This is a heuristic.
            if acceleration < self.braking_threshold:
                flags.append('Sudden Braking')
        
        return flags
