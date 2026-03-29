"""
CLI prediction using the same 3-feature layout as backend RiskModel.
"""

import pickle
import pandas as pd
from pathlib import Path

FEATURE_COLS = ["wind_speed", "rainfall", "population_density"]

MODEL_PATH = Path(__file__).parent / "models" / "risk_model.pkl"


def load_model():
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


def predict_risk(wind_speed, rainfall, population_density):
    """
    Predict risk score (0-1). population_density: "Low" | "Medium" | "High".
    """
    model = load_model()
    pop_map = {"Low": 0, "Medium": 1, "High": 2}
    pop_encoded = pop_map.get(population_density, 1)

    if model:
        X = pd.DataFrame(
            [[wind_speed, rainfall, pop_encoded]],
            columns=FEATURE_COLS,
        )
        risk = model.predict(X)[0]
    else:
        risk = (
            (wind_speed / 150) * 0.5
            + (rainfall / 20) * 0.3
            + (pop_encoded / 2) * 0.2
        )

    return float(min(1.0, max(0.0, risk)))


def get_risk_level(risk_score):
    if risk_score >= 0.7:
        return "HIGH", "red"
    elif risk_score >= 0.4:
        return "MEDIUM", "yellow"
    else:
        return "LOW", "green"


if __name__ == "__main__":
    print("=" * 50)
    print("RISK PREDICTION TEST")
    print("=" * 50)

    test_cases = [
        {"wind": 120, "rain": 10, "pop": "High", "desc": "Strong storm"},
        {"wind": 75, "rain": 5, "pop": "Medium", "desc": "Moderate"},
        {"wind": 40, "rain": 2, "pop": "Low", "desc": "Light"},
        {"wind": 15, "rain": 0.5, "pop": "Low", "desc": "Calm"},
    ]

    for case in test_cases:
        risk = predict_risk(case["wind"], case["rain"], case["pop"])
        level, _ = get_risk_level(risk)
        print(f"\n{case['desc']}:")
        print(
            f"   Wind: {case['wind']} mph, Rain: {case['rain']} in, Pop: {case['pop']}"
        )
        print(f"   Risk: {risk:.1%} {level}")
