import argparse
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from app.ml.features import FEATURE_COLUMNS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="models/spam_risk.joblib")
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    required = set(FEATURE_COLUMNS + ["is_spam"])
    missing = required - set(data.columns)
    if missing:
        raise SystemExit(f"Dataset missing columns: {sorted(missing)}")
    data = data[list(required)].replace([float("inf"), float("-inf")], pd.NA).dropna()
    if data["is_spam"].nunique() != 2:
        raise SystemExit("is_spam must contain both 0 and 1 labels.")
    x = data[FEATURE_COLUMNS].astype(float)
    y = data["is_spam"].astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y)
    model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
        RandomForestClassifier(n_estimators=300, class_weight="balanced",
                               random_state=42, n_jobs=-1))
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    print(classification_report(y_test, prediction, zero_division=0))
    if hasattr(model[-1], "predict_proba") and y_test.nunique() == 2:
        print("ROC-AUC:", round(roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]), 4))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    print(f"Saved model to {output}. Validate on independent real data before production.")

if __name__ == "__main__":
    main()
