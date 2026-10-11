"""f1_eval.py: shared evaluation function for the F1 podium project (owner: P4).
Usage: from f1_eval import evaluate, train_eval
Same code as notebooks/p4_models.ipynb, section 4.1 (like f1_clean.py and P1's notebook)."""

import pandas as pd
from sklearn.metrics import (average_precision_score, f1_score, precision_score,
                             recall_score, roc_auc_score)


def evaluate(model, X, y, threshold=0.5):
    """Score an already-fitted model on one split and return the 5 metrics.
    ROC-AUC and PR-AUC use the probabilities (no threshold needed);
    F1, precision and recall use the yes/no prediction at `threshold`."""
    proba = model.predict_proba(X)[:, 1]          # predicted probability of a podium
    pred = (proba >= threshold).astype(int)       # 1 = "podium" at this threshold
    return {
        "ROC-AUC": roc_auc_score(y, proba),
        "PR-AUC": average_precision_score(y, proba),
        "F1": f1_score(y, pred, zero_division=0),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
    }


def train_eval(model, X_train, y_train, X_val, y_val, threshold=0.5, name="model"):
    """Fit `model` on the training years only, then score it on train and validation.
    The test set is not used here on purpose: it is scored once, at the end, with evaluate()."""
    model.fit(X_train, y_train)
    rows = [
        {"model": name, "split": "train", **evaluate(model, X_train, y_train, threshold)},
        {"model": name, "split": "validation", **evaluate(model, X_val, y_val, threshold)},
    ]
    return pd.DataFrame(rows).round(4)
