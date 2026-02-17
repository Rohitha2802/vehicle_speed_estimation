from deep_sort_realtime.deepsort_tracker import DeepSort

class VehicleTracker:
    def __init__(self, max_age=30, n_init=3, nms_max_overlap=1.0):
        """
        Initialize the Vehicle Tracker using DeepSORT.

        Args:
            max_age (int): Maximum number of missed frames before a track is deleted.
            n_init (int): Minimum number of consecutive detections to verify a track.
            nms_max_overlap (float): NMS threshold.
        """
        print("Initializing DeepSORT tracker...")
        self.tracker = DeepSort(max_age=max_age, n_init=n_init, nms_max_overlap=nms_max_overlap)

    def update_tracks(self, detections, frame):
        """
        Update tracks with new detections.

        Args:
            detections (list): List of detections [[x1, y1, x2, y2, score, class_id], ...]
            frame (numpy.ndarray): Current frame (used for feature extraction).

        Returns:
            list: List of tracks objects. Each track has attributes: track_id, to_tlbr().
        """
        # DeepSORT expects detections in format: [[left, top, w, h], confidence, detection_class]
        formatted_detections = []
        
        for det in detections:
            x1, y1, x2, y2, conf, cls_id = det
            w = x2 - x1
            h = y2 - y1
            # DeepSORT expects [left, top, w, h]
            formatted_detections.append([[x1, y1, w, h], conf, cls_id])

        # Update tracker
        tracks = self.tracker.update_tracks(formatted_detections, frame=frame)
        
        confirmed_tracks = []
        for track in tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            confirmed_tracks.append(track)
            
        return confirmed_tracks
