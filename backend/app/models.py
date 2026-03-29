import pickle
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "ml" / "models" / "risk_model.pkl"

class RiskModel:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            if MODEL_PATH.exists():
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                print("Model loaded")
            else:
                print("Using fallback (no pickle model)")
                self.model = None
        except Exception as e:
            print(f"Model load error: {e}")
            self.model = None

    def predict(self, wind_speed: float, rainfall: float, population_density: str) -> float:
        pop_map = {"Low": 0, "Medium": 1, "High": 2}
        pop_encoded = pop_map.get(population_density, 1)

        if self.model:
            features = np.array([[wind_speed, rainfall, pop_encoded]])
            risk = self.model.predict(features)[0]
        else:
            wind_factor = min(wind_speed / 150, 1.0) * 0.5
            rain_factor = min(rainfall / 20, 1.0) * 0.3
            pop_factors = {"Low": 0.05, "Medium": 0.12, "High": 0.2}
            pop_factor = pop_factors.get(population_density, 0.12)
            risk = wind_factor + rain_factor + pop_factor

        return min(1.0, max(0.0, risk))

risk_model = RiskModel()
