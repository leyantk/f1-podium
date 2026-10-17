"""f1_eval.py: shared evaluation function for the F1 podium project (owner: P4).
Usage: from f1_eval import evaluate, train_eval
Same code as notebooks/p4_models.ipynb, section 4.1 (like f1_clean.py and P1's notebook).
`sample_weight` is optional in both functions, so calls without it work exactly as before."""

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, f1_score, precision_score,
                             recall_score, roc_auc_score)


def evaluate(model, X, y, threshold=0.5, sample_weight=None):
    """Score an already-fitted model on one split and return the 5 metrics.
    ROC-AUC and PR-AUC use the probabilities (no threshold needed);
    F1, precision and recall use the yes/no prediction at `threshold`.
    `sample_weight` (optional) weights the rows, as in training."""
    proba = model.predict_proba(X)[:, 1]          # predicted probability of a podium
    pred = (proba >= threshold).astype(int)       # 1 = "podium" at this threshold
    w = sample_weight
    return {
        "ROC-AUC": roc_auc_score(y, proba, sample_weight=w),
        "PR-AUC": average_precision_score(y, proba, sample_weight=w),
        "F1": f1_score(y, pred, sample_weight=w, zero_division=0),
        "precision": precision_score(y, pred, sample_weight=w, zero_division=0),
        "recall": recall_score(y, pred, sample_weight=w, zero_division=0),
    }


def train_eval(model, X_train, y_train, X_val, y_val, threshold=0.5, name="model", sample_weight=None):
    """Fit `model` on the training years only, then score it on train and validation.
    `sample_weight` (optional): one weight per training row (P3's `sample_weight` column). It is passed to fit
    (to the last step of a pipeline) and used for the training scores. Validation rows are not weighted.
    The test set is not used here on purpose: it is scored once, at the end, with evaluate()."""
    if sample_weight is None:
        model.fit(X_train, y_train)
    else:
        sample_weight = np.asarray(sample_weight, dtype=float)
        key = f"{model.steps[-1][0]}__sample_weight" if hasattr(model, "steps") else "sample_weight"
        model.fit(X_train, y_train, **{key: sample_weight})
    rows = [
        {"model": name, "split": "train", **evaluate(model, X_train, y_train, threshold, sample_weight)},
        {"model": name, "split": "validation", **evaluate(model, X_val, y_val, threshold)},
    ]
    return pd.DataFrame(rows).round(4)
