class RiskPredictor:
    def __init__(self):
        """
        Initialize Risk Predictor.
        Potential to load LSTM model here if available.
        """
        pass

    def calculate_risk(self, flags):
        """
        Calculate a simple risk score based on behavior flags.

        Args:
            flags (list): List of behavior string flags.

        Returns:
            float: Risk score (0.0 to 1.0)
        """
        score = 0.0
        
        if 'Overspeeding' in flags:
            score += 0.4
        if 'Zig-Zag' in flags:
            score += 0.3
        if 'Sudden Braking' in flags:
            score += 0.3
            
        return min(score, 1.0)
