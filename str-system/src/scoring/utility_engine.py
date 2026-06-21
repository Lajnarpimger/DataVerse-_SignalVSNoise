import json
from typing import Dict, Any

class UtilityEngine:
    """
    Stage 6: Utility Score Engine (Deterministic)
    Calculates final utility score combining coverage, validation, signal, and noise.
    """
    def __init__(self, config_path: str = "config/weights.json"):
        with open(config_path, 'r') as f:
            self.weights = json.load(f)
            
        self.w_coverage = self.weights.get("w_coverage", 0.25)
        self.w_validation = self.weights.get("w_validation", 0.15)
        self.w_signal = self.weights.get("w_signal", 0.60)
        
    def calculate_score(self, coverage: float, validation: float, signal_score: float, noise_score: float) -> float:
        """
        base_score = (w_coverage × coverage) + (w_validation × validation) + (w_signal × signal)
        final_score = base_score × (1 - noise)
        Clamp to [0, 1]
        """
        base_score = (self.w_coverage * coverage) + \
                     (self.w_validation * validation) + \
                     (self.w_signal * signal_score)
                     
        final_score = base_score * (1.0 - noise_score)
        
        # Clamp between 0.0 and 1.0
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score
