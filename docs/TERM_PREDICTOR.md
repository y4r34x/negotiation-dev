# Term Predictor

A Random Forest model that predicts likely contract terms from partial input. Given some known contract terms (e.g., "has Audit Rights"), it predicts the most likely values for unknown terms based on patterns learned from the CUAD dataset.

## Installation

```bash
# Install with ML dependencies
pip install -e ".[ml]"
```

## CLI Usage

### Predict Missing Terms

Provide known terms as flags, get predictions for the rest:

```bash
negotiate predict --audit-rights yes --anti-assignment no
```

Output:
```
Known terms: {'Audit Rights': 1, 'Anti-Assignment': 0}

=== Predictions ===

Cap On Liability                    Yes  (78%) ███████████████
Revenue/Profit Sharing              No   (65%) █████████████
...
```

### Evaluate Model Accuracy

Run 5-fold cross-validation to see how well each term can be predicted:

```bash
negotiate predict --evaluate
```

Output:
```
Term                                  Accuracy   Baseline     Lift
-----------------------------------------------------------------
Cap On Liability                         76.3%      53.9%   +22.4%
Audit Rights                             75.1%      58.0%   +17.1%
...
```

- **Accuracy**: Cross-validated accuracy on held-out data
- **Baseline**: Accuracy if you always predict the majority class
- **Lift**: How much better the model is than guessing

### Show Feature Importance

See which terms are most predictive of each other:

```bash
negotiate predict --importance
```

Output:
```
Cap On Liability:
  Uncapped Liability: 0.324
  Audit Rights: 0.209
  Anti-Assignment: 0.138
```

## Python API

```python
from negotiation.models import TermPredictor

# Initialize and train
predictor = TermPredictor()
predictor.fit('data/training/cuad.tsv')

# Predict missing terms
known = {'Audit Rights': 1, 'Cap On Liability': 1}
predictions = predictor.predict(known)

for term, result in predictions.items():
    print(f"{term}: {result['prediction']} ({result['probability']:.0%})")

# Evaluate model
scores = predictor.evaluate(cv_folds=5)
for term, score in scores.items():
    print(f"{term}: {score['accuracy']:.1%} accuracy, {score['lift']:+.1%} lift")

# Feature importance
importance = predictor.feature_importance()
```

## Available Terms

The model predicts these binary (yes/no) contract terms:

| Term | Description |
|------|-------------|
| Termination For Convenience | Party can terminate without cause |
| Change Of Control | Provisions for ownership changes |
| Anti-Assignment | Restrictions on assigning the contract |
| Revenue/Profit Sharing | Parties share revenue or profits |
| Ip Ownership Assignment | IP ownership transfers to a party |
| Joint Ip Ownership | IP owned jointly by parties |
| Non-Transferable License | License cannot be transferred |
| Source Code Escrow | Source code held in escrow |
| Post-Termination Services | Services continue after termination |
| Audit Rights | Right to audit the other party |
| Uncapped Liability | No limit on liability |
| Cap On Liability | Liability is capped |
| Liquidated Damages | Pre-agreed damages for breach |

## Model Performance

Based on 510 contracts from the CUAD dataset:

| Term | Predictable? | Notes |
|------|--------------|-------|
| Cap On Liability | Yes (+22% lift) | Strong signal from Audit Rights, Uncapped Liability |
| Audit Rights | Yes (+17% lift) | Strong signal from Cap On Liability, Post-Termination |
| Anti-Assignment | Moderate (+7% lift) | Correlated with Audit Rights |
| Source Code Escrow | No (rare term) | 97% are "No", model just predicts majority |
| Joint Ip Ownership | No (rare term) | 91% are "No", model just predicts majority |

## How It Works

1. **Training**: Loads CUAD data, encodes Yes/No as 1/0, trains one Random Forest per term
2. **Prediction**: For each unknown term, uses the other terms as features to predict
3. **Regularization**: Uses `max_depth=5` and `min_samples_leaf=10` to prevent overfitting on the small dataset

The model learns correlations like:
- Contracts with Audit Rights are 2x more likely to have Cap On Liability
- Revenue Sharing contracts tend to have Anti-Assignment clauses
