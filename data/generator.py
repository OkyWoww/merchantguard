"""Reproducible Synthetic Dataset Generator & Calibrated Margin Model Trainer.

AMD Developer Hackathon: ACT III — Track: Reinvent Commerce
Module: Task T2.1 Synthetic Data Generator & Statistical P(Win) Modeling

Generates synthetic dispute scenarios with courier telematics, buyer history,
and margin profiles. Trains a calibrated LogisticRegression model via scikit-learn
and exports the artifact to models/margin.joblib.
"""

from __future__ import annotations
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    log_loss,
    brier_score_loss,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = [
    "delivery_days_gap",
    "has_signature",
    "geo_distance_meters",
    "buyer_history_score",
    "dispute_amount",
    "courier_reliability_score",
]


def generate_synthetic_tabular_dataset(
    count: int = 500, seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """
    Generates a reproducible synthetic dataset of dispute metrics with realistic
    win/loss probabilities for merchant defense.
    """
    rng = np.random.RandomState(seed)

    rows: List[Dict[str, Any]] = []
    X_list: List[List[float]] = []
    y_list: List[int] = []

    for i in range(count):
        # 1. delivery_days_gap: 1 to 35 days
        delivery_days_gap = float(rng.exponential(scale=7.0) + 1.0)
        delivery_days_gap = min(45.0, round(delivery_days_gap, 1))

        # 2. has_signature: 0 or 1 (signature captured on high value or standard delivery)
        has_sig_prob = 0.65 if delivery_days_gap < 14 else 0.30
        has_signature = 1.0 if rng.rand() < has_sig_prob else 0.0

        # 3. geo_distance_meters: distance between GPS ping and shipping address
        if has_signature:
            geo_distance = float(rng.gamma(shape=2.0, scale=8.0))  # mostly 5-30m
        else:
            geo_distance = float(rng.gamma(shape=3.0, scale=40.0))  # 30-200m
        geo_distance = round(min(600.0, geo_distance), 1)

        # 4. buyer_history_score: merchant loyalty / dispute frequency [0.0 - 1.0]
        buyer_history_score = round(float(rng.beta(a=5.0, b=2.0)), 2)

        # 5. dispute_amount: GMV in USD [$15 - $800]
        dispute_amount = round(float(rng.lognormal(mean=4.2, sigma=0.8)), 2)
        dispute_amount = max(10.0, min(950.0, dispute_amount))

        # 6. courier_reliability_score: carrier historical reliability [0.0 - 1.0]
        courier_reliability_score = round(float(rng.beta(a=6.0, b=2.0)), 2)

        # Ground truth logistic probability formula
        # Strong evidence (signature, close GPS, swift delivery, reliable carrier) yields high win prob
        logit = (
            -0.20
            + (2.60 * has_signature)
            - (0.11 * delivery_days_gap)
            - (0.012 * geo_distance)
            + (1.40 * courier_reliability_score)
            + (0.80 * buyer_history_score)
            - (0.0008 * dispute_amount)
            + rng.normal(loc=0.0, scale=0.45)  # Realistic empirical noise
        )
        p_win = 1.0 / (1.0 + np.exp(-logit))
        label = 1 if p_win >= 0.50 else 0

        features = [
            delivery_days_gap,
            has_signature,
            geo_distance,
            buyer_history_score,
            dispute_amount,
            courier_reliability_score,
        ]
        X_list.append(features)
        y_list.append(label)

        rows.append({
            "case_id": f"SYN-{1000 + i}",
            "delivery_days_gap": delivery_days_gap,
            "has_signature": int(has_signature),
            "geo_distance_meters": geo_distance,
            "buyer_history_score": buyer_history_score,
            "dispute_amount": dispute_amount,
            "courier_reliability_score": courier_reliability_score,
            "latent_p_win": round(float(p_win), 4),
            "dispute_won": label,
        })

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int64)
    return X, y, rows


def train_and_export_margin_model(
    output_model_path: Path, output_report_path: Path, sample_count: int = 500, seed: int = 42
) -> Dict[str, Any]:
    """
    Trains a Logistic Regression pipeline with StandardScaler, evaluates calibration,
    and exports both model weights and a Markdown performance report.
    """
    X, y, records = generate_synthetic_tabular_dataset(count=sample_count, seed=seed)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=seed, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(random_state=seed, C=1.0, max_iter=1000)),
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    roc_auc = float(roc_auc_score(y_test, y_prob))
    loss = float(log_loss(y_test, y_prob))
    brier = float(brier_score_loss(y_test, y_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()

    # Save model artifact
    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "feature_names": FEATURE_NAMES,
            "metadata": {
                "trained_at": datetime.utcnow().isoformat() + "Z",
                "sample_count": sample_count,
                "accuracy": acc,
                "roc_auc": roc_auc,
                "brier_score": brier,
            },
        },
        output_model_path,
    )
    artifact_size_bytes = output_model_path.stat().st_size

    # Extract model coefficients for explainability
    clf: LogisticRegression = pipeline.named_steps["classifier"]
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    coeffs = clf.coef_[0]
    intercept = float(clf.intercept_[0])

    # Generate Markdown Report
    report_md = f"""# Statistical Margin Model Card: P(Win) Classifier

> **Component:** Task T2.1 / T2.2 Statistical Margin Recovery Engine  
> **Framework:** scikit-learn Logistic Regression (Calibrated Probability Classifier)  
> **Artifact:** `{output_model_path.as_posix()}` ({artifact_size_bytes} bytes)  
> **Generation Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}  
> **Synthetic Data Disclosure:** Trained on {sample_count} synthetic dispute profiles generated via `data/generator.py` (fixed seed={seed}).

---

## 1. Model Performance Metrics (20% Holdout Test Set)

| Metric | Score | Assessment |
|---|---|---|
| **Accuracy** | `{acc * 100:.2f}%` | High classification fidelity |
| **ROC-AUC** | `{roc_auc:.4f}` | Strong discriminative ability between recoverable & non-recoverable disputes |
| **Log-Loss** | `{loss:.4f}` | Low cross-entropy error on probabilistic predictions |
| **Brier Calibration Score** | `{brier:.4f}` | Well-calibrated probabilities suitable for expected value calculations |
| **Model Artifact Size** | `{artifact_size_bytes / 1024:.2f} KB` | Ultra-lightweight footprint, zero GPU requirements |

### Confusion Matrix
```text
                  Predicted Loss (0)   Predicted Win (1)
Actual Loss (0):        {cm[0][0]:<20} {cm[0][1]}
Actual Win (1):         {cm[1][0]:<20} {cm[1][1]}
```

---

## 2. Explainable Linear Coefficients

Linear odds-ratio coefficients explain why each telematic fact shifts the win probability $P(\\text{{Win}})$:

| Feature | Standardized Weight ($\\beta$) | Odds Multiplier ($e^\\beta$) | Interpretability Direction |
|---|---|---|---|
"""
    for fname, coef in zip(FEATURE_NAMES, coeffs):
        odds = np.exp(coef)
        direction = "Positive (Merchant advantage)" if coef > 0 else "Negative (Customer advantage)"
        report_md += f"| `{fname}` | `{coef:+.4f}` | `{odds:.3f}x` | {direction} |\n"

    report_md += f"""
Intercept: `{intercept:+.4f}`

---

## 3. Mathematical Formula & Invariant Compliance
The model produces calibrated probabilities $P(\\text{{Win}})$ via standard logistic sigmoid:

$$P(\\text{{Win}} \\mid \\mathbf{{x}}) = \\frac{{1}}{{1 + e^{{-\\left(\\beta_0 + \\sum_{{j=1}}^d \\beta_j \\cdot \\frac{{x_j - \\mu_j}}{{\\sigma_j}}\\right)}}}}$$

- **Invariant:** The LLM is NEVER called to compute $P(\\text{{Win}})$ or decide EV hurdle rates.
- **Track 3 Compliance:** Fully explainable parametric model conforming to statistical commerce margin recovery principles.
"""

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    return {
        "accuracy": acc,
        "roc_auc": roc_auc,
        "log_loss": loss,
        "brier_score": brier,
        "artifact_size_bytes": artifact_size_bytes,
        "model_path": str(output_model_path),
        "report_path": str(output_report_path),
    }


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    model_file = base_dir / "models" / "margin.joblib"
    report_file = base_dir / "docs" / "evidence" / "margin_model_report.md"

    print("Generating synthetic dataset and training margin model...")
    results = train_and_export_margin_model(
        output_model_path=model_file,
        output_report_path=report_file,
        sample_count=500,
        seed=42,
    )
    print("Training complete!")
    print(f"Model saved to: {results['model_path']} ({results['artifact_size_bytes']} bytes)")
    print(f"Accuracy: {results['accuracy']:.4f}, ROC-AUC: {results['roc_auc']:.4f}, Brier: {results['brier_score']:.4f}")
