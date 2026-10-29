import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_COLUMNS


def evaluate_model(name: str, pipeline, x_train, y_train, x_test, y_test, cv):
    cv_scores = cross_val_score(pipeline, x_train, y_train, cv=cv, scoring="roc_auc")
    pipeline.fit(x_train, y_train)
    y_pred = pipeline.predict(x_test)
    y_prob = pipeline.predict_proba(x_test)[:, 1] if hasattr(pipeline[-1], "predict_proba") else y_pred

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    cv_mean = np.mean(cv_scores)
    cv_std = np.std(cv_scores)

    return {
        "Model": name,
        "Accuracy": round(acc, 4),
        "Precision": round(prec, 4),
        "Recall": round(rec, 4),
        "Macro F1": round(f1, 4),
        "Test ROC-AUC": round(auc, 4),
        "5-Fold CV AUC": f"{cv_mean:.4f} ± {cv_std:.4f}",
    }

def main():
    parser = argparse.ArgumentParser(description="Train and validate backlink spam-risk ML models.")
    parser.add_argument("--input", required=True, help="Path to labeled_backlinks.csv")
    parser.add_argument("--output", default="models/spam_risk.joblib", help="Output model joblib path")
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    required = set(FEATURE_COLUMNS + ["is_spam"])
    missing = required - set(data.columns)
    if missing:
        raise SystemExit(f"Dataset missing required columns: {sorted(missing)}")

    data = data[list(required)].replace([float("inf"), float("-inf")], pd.NA).dropna()
    if data["is_spam"].nunique() != 2:
        raise SystemExit("Dataset must contain both 0 and 1 classes for is_spam.")

    x = data[FEATURE_COLUMNS].astype(float)
    y = data["is_spam"].astype(int)

    # Stratified Train/Test Split (80% train, 20% independent holdout)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # 1. Define Model Pipelines
    models = [
        ("Dummy (Prior)", make_pipeline(
            SimpleImputer(strategy="median"),
            DummyClassifier(strategy="most_frequent")
        )),
        ("Dummy (Stratified)", make_pipeline(
            SimpleImputer(strategy="median"),
            DummyClassifier(strategy="stratified", random_state=42)
        )),
        ("Logistic Regression (L2)", make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=42)
        )),
        ("Random Forest (Champion)", make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            RandomForestClassifier(
                n_estimators=300,
                max_depth=10,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            )
        )),
    ]

    print("=" * 80)
    print("LinkIntel AI — Machine Learning Benchmark & Cross-Validation")
    print(f"Dataset: {args.input} | Total Rows: {len(data)} | Holdout Test: {len(x_test)}")
    print("=" * 80)

    results = []
    for name, pipe in models:
        metrics = evaluate_model(name, pipe, x_train, y_train, x_test, y_test, cv)
        results.append(metrics)

    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    print("=" * 80)

    # Final champion detailed evaluation
    champion_pipe = models[-1][1]
    y_pred = champion_pipe.predict(x_test)
    print("\nChampion Model (Random Forest) Hold-out Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Feature Importances
    rf_step = champion_pipe.named_steps["randomforestclassifier"]
    importances = pd.Series(rf_step.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    print("Feature Importances:")
    for feat, imp in importances.items():
        print(f"  - {feat:22s}: {imp:.4f} ({imp*100:.1f}%)")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion_pipe, output_path)
    print(f"\nSaved production pipeline to {output_path}")

if __name__ == "__main__":
    main()

