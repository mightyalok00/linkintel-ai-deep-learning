from pathlib import Path
import joblib
import pandas as pd
from app.config import settings
from app.ml.features import FEATURE_COLUMNS

def predict_spam_risk(feature_row: dict) -> float | None:
    if not settings.enable_spam_model:
        return None
    model_path = Path(settings.spam_model_path)
    if not model_path.exists():
        return None
    try:
        model = joblib.load(model_path)
        row_df = pd.DataFrame([[float(feature_row[c]) for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        probabilities = model.predict_proba(row_df)
        # Positive class is assumed to be label 1 = spam.
        classes = list(model.classes_)
        if 1 not in classes:
            return None
        probability = float(probabilities[0][classes.index(1)])
        return round(probability * 100, 2)
    except (ValueError, OSError, KeyError, AttributeError):
        return None
