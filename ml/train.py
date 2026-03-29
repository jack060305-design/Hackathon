"""
Train machine learning model for disaster risk prediction.
Uses 3 features (wind, rain, population encoded) to match backend app/models.py.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def generate_training_data(n_samples=2000):
    """Generate synthetic training data."""
    np.random.seed(42)

    wind_speed = np.random.uniform(0, 150, n_samples)
    rainfall = np.random.uniform(0, 20, n_samples)
    population_density = np.random.choice([0, 1, 2], n_samples)

    risk = (
        (wind_speed / 150) * 0.5 +
        (rainfall / 20) * 0.3 +
        (population_density / 2) * 0.2
    )
    risk += np.random.normal(0, 0.05, n_samples)
    risk = np.clip(risk, 0, 1)

    return pd.DataFrame({
        "wind_speed": wind_speed,
        "rainfall": rainfall,
        "population_density": population_density,
        "risk_score": risk,
    })


def train_model():
    print("Generating training data...")
    df = generate_training_data(3000)

    feature_cols = ["wind_speed", "rainfall", "population_density"]
    X = df[feature_cols]
    y = df["risk_score"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")

    print("Training Random Forest model...")
    model = RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"\nModel Performance:")
    print(f"   Mean Absolute Error: {mean_absolute_error(y_test, y_pred):.3f}")
    print(f"   R2 Score: {r2_score(y_test, y_pred):.3f}")

    model_path = MODEL_DIR / "risk_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"\nModel saved to: {model_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("DISASTER RISK MODEL TRAINING")
    print("=" * 50)
    train_model()
    print("\nTraining complete.")
