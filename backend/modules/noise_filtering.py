import numpy as np
from filterpy.kalman import KalmanFilter

class TrajectorySmoother:
    def __init__(self):
        """
        Initialize the Trajectory Smoother using a dictionary of Kalman Filters.
        Each track_id gets its own KF.
        """
        self.filters = {}  # track_id -> KalmanFilter

    def _create_kalman_filter(self, initial_x, initial_y):
        """
        Create a constant velocity Kalman Filter.
        """
        kf = KalmanFilter(dim_x=4, dim_z=2)
        # State: [x, y, dx, dy]
        kf.x = np.array([initial_x, initial_y, 0., 0.])
        
        # State Transition Matrix (F)
        # x = x + dx*dt
        kf.F = np.array([[1, 0, 1, 0],
                         [0, 1, 0, 1],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])
        
        # Measurement Function (H) -> we measure [x, y]
        kf.H = np.array([[1, 0, 0, 0],
                         [0, 1, 0, 0]])
        
        # Measurement Noise (R)
        kf.R *= 1.
        
        # Process Noise (Q)
        kf.Q *= 0.1
        
        # Error Covariance (P)
        kf.P *= 10.
        
        return kf

    def smooth(self, track_id, x, y):
        """
        Apply Kalman Filter smoothing to a centroid (x, y).

        Args:
            track_id (int): Unique track ID.
            x (float): Measured X position.
            y (float): Measured Y position.

        Returns:
            tuple: (smoothed_x, smoothed_y)
        """
        if track_id not in self.filters:
            self.filters[track_id] = self._create_kalman_filter(x, y)
        
        kf = self.filters[track_id]
        
        # Predict
        kf.predict()
        
        # Update with measurement
        kf.update(np.array([x, y]))
        
        # Return smoothed state
        return kf.x[0], kf.x[1]
