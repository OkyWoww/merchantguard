# Statistical Margin Model Card: P(Win) Classifier

> **Component:** Task T2.1 / T2.2 Statistical Margin Recovery Engine  
> **Framework:** scikit-learn Logistic Regression (Calibrated Probability Classifier)  
> **Artifact:** `C:/Users/ADMIN/Documents/merchantguard/models/margin.joblib` (1821 bytes)  
> **Generation Date:** 2026-10-13 05:25:07Z  
> **Synthetic Data Disclosure:** Trained on 500 synthetic dispute profiles generated via `data/generator.py` (fixed seed=42).

---

## 1. Model Performance Metrics (20% Holdout Test Set)

| Metric | Score | Assessment |
|---|---|---|
| **Accuracy** | `97.00%` | High classification fidelity |
| **ROC-AUC** | `0.9996` | Strong discriminative ability between recoverable & non-recoverable disputes |
| **Log-Loss** | `0.0649` | Low cross-entropy error on probabilistic predictions |
| **Brier Calibration Score** | `0.0184` | Well-calibrated probabilities suitable for expected value calculations |
| **Model Artifact Size** | `1.78 KB` | Ultra-lightweight footprint, zero GPU requirements |

### Confusion Matrix
```text
                  Predicted Loss (0)   Predicted Win (1)
Actual Loss (0):        34                   0
Actual Win (1):         3                    63
```

---

## 2. Explainable Linear Coefficients

Linear odds-ratio coefficients explain why each telematic fact shifts the win probability $P(\text{Win})$:

| Feature | Standardized Weight ($\beta$) | Odds Multiplier ($e^\beta$) | Interpretability Direction |
|---|---|---|---|
| `delivery_days_gap` | `-1.4708` | `0.230x` | Negative (Customer advantage) |
| `has_signature` | `+2.6841` | `14.645x` | Positive (Merchant advantage) |
| `geo_distance_meters` | `-1.9522` | `0.142x` | Negative (Customer advantage) |
| `buyer_history_score` | `+0.4351` | `1.545x` | Positive (Merchant advantage) |
| `dispute_amount` | `+0.1452` | `1.156x` | Positive (Merchant advantage) |
| `courier_reliability_score` | `+0.6027` | `1.827x` | Positive (Merchant advantage) |

Intercept: `+2.5762`

---

## 3. Mathematical Formula & Invariant Compliance
The model produces calibrated probabilities $P(\text{Win})$ via standard logistic sigmoid:

$$P(\text{Win} \mid \mathbf{x}) = \frac{1}{1 + e^{-\left(\beta_0 + \sum_{j=1}^d \beta_j \cdot \frac{x_j - \mu_j}{\sigma_j}\right)}}$$

- **Invariant:** The LLM is NEVER called to compute $P(\text{Win})$ or decide EV hurdle rates.
- **Track 3 Compliance:** Fully explainable parametric model conforming to statistical commerce margin recovery principles.
