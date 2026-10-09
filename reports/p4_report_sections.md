# Report sections from Part 4 (models, metrics, XAI, limitations)

Source of every number: `notebooks/p4_models.ipynb` (sections 4.1-4.13), run on P3's modeling table
(18 features, train 2003-2019, validation 2020-2021, test 2022-2024).

## 1. Models

All models use the same table, the same 18 features and one shared preprocessing pipeline, fitted on the
training years only: median imputation with a missing-value indicator for every feature with gaps
(standings are empty in round 1, form in a driver's first race), standardization, and one-hot encoding of `era`.

| Model | How it works (one sentence) | Settings after tuning on validation |
|---|---|---|
| Rule `grid <= 3` (baseline) | Predicts a podium for the three cars that start at the front. | none |
| Logistic regression (baseline, **final**) | Weighted sum of the features turned into a probability by the sigmoid. | `C=10` |
| Random forest | Average vote of 300 trees, each trained on random rows and features. | `max_features="sqrt"`, `min_samples_leaf=5`, balanced classes |
| Gradient boosting | Small trees built one after another, each correcting the previous ones. | `learning_rate=0.03`, `max_leaf_nodes=7`, balanced classes |
| Shallow neural network (PyTorch) | Two hidden layers (64, 32) with ReLU and dropout 0.2, early stopping on validation loss. | `pos_weight` for the imbalance, seed and one CPU thread for reproducibility |

Twelve modeling attempts, each in its own notebook cell with its result: three baselines (rule, logistic
regression, balanced logistic regression), logistic regression on the 4 draft features, random forest,
gradient boosting, two networks, and one tuning grid per model.

## 2. Metric choice

* **Primary metric: PR-AUC** (average precision). Podiums are about 15% of rows; PR-AUC measures how well the
  real podium finishers are ranked at the top, needs no threshold, and its floor is the podium rate (0.151),
  not 0.5. A model that always says "no podium" has 84.9% accuracy, which is why accuracy is not used.
* **Secondary metric: F1** at a threshold chosen on validation (highest F1 between 0.05 and 0.95).
* ROC-AUC, precision and recall are reported for completeness.
* **Final model choice (validation only):** the bootstrap standard error of the validation PR-AUC is 0.040;
  all four tuned models are within one standard error of the best (network, 0.752), so the
  one-standard-error rule picks the simplest: **logistic regression, threshold 0.23**.

## 3. Comparison table (PR-AUC / F1, threshold from validation)

| Model | Train | Validation | Test (used once) |
|---|---|---|---|
| Rule `grid <= 3` | 0.470 / 0.648 | 0.530 / 0.695 | 0.474 / 0.649 |
| **Logistic regression (final)** | 0.691 / 0.666 | 0.738 / 0.717 | **0.712** / 0.581 |
| Random forest | 0.908 / 0.802 | 0.729 / 0.706 | 0.678 / 0.617 |
| Gradient boosting | 0.712 / 0.681 | 0.729 / 0.713 | 0.690 / 0.689 |
| Neural network | 0.704 / 0.682 | 0.752 / 0.717 | 0.698 / 0.672 |

* P3's features add real information: the same logistic regression reaches validation PR-AUC 0.672 with the
  4 draft features and 0.738 with the 18 features.
* On the test set the final model has the **best ranking** (PR-AUC 0.712, ROC-AUC 0.936; no-skill floor 0.151),
  but the **weakest F1** (0.581: recall 0.95, precision 0.42; 194 of 204 podiums found, 270 false alarms).
  Cause: the test seasons belong to the `ground_effect` era, which never occurs in training; logistic
  regression learned negative weights for both known eras (-1.28, -1.12), so every test row gets the same
  upward push (about 5 predicted podiums per race instead of 3). A uniform push does not change the ranking
  but moves many rows over the low threshold. Nothing was changed after seeing the test results.
* The random forest overfits (train PR-AUC 0.908, test 0.678); default gradient boosting overfitted too
  (train 0.932 vs validation 0.704) until tuning chose small trees.

## 4. Explainability (XAI)

* **Permutation importance (validation PR-AUC drop):** `qual_position` 0.174, `grid` 0.092, all others below
  0.03. Per feature group (shuffled together): qualifying 0.105, grid 0.101, standings 0.057, form 0.027,
  circuit 0.005, context -0.003.
* **SHAP:** a position nearer the front (qualifying, grid, championship) and good recent form push the
  probability up. Correlated inputs produce surprising single signs (`reached_q3 = 1` pushes down given the
  exact qualifying position).
* **Local examples:** Hamilton, Bahrain 2020 (pole, won): baseline 0.16, grid +0.21, form +0.16, qualifying
  +0.14, leading the championship +0.09 -> 0.924. Ocon, Italy 2020 (grid 12, 8th): -> 0.015.
  LIME agrees on the direction but approximates poorly (0.34 vs 0.92, R^2 0.55); SHAP adds up exactly.
* **Most confident miss:** Hamilton, Italy 2020: pole, 90.9%, finished 7th after an in-race penalty.
* **Not causal:** the explanations describe how the model uses the features, not what causes a podium. A fast
  car and driver cause both the good starting position and the podium; the model uses the position as a signal.

## 5. Model limitations

* Era sensitivity: rules, cars and the points system change (25 points for a win since 2010, 10 before); the
  test era is unseen in training and shifts the probabilities (above).
* Qualifying coverage: the table starts in 2003 because older qualifying data is missing or in other formats.
* Missing values carry meaning: a missing qualifying time in training almost always means a driver who set no
  time, so a pole-sitter with a data gap gets about 1%; predictions for incomplete records are unreliable.
* `best_qual_s` depends on the circuit length (only comparable within a race).
* Small validation set (117 podiums, PR-AUC standard error 0.04): the ranking of the tuned models is uncertain.
* The threshold maximizes F1, i.e. treats missed podiums and false alarms as equally bad.
* In-race events (incidents, penalties, safety cars, weather, strategy) cannot be predicted before the race.
* Per model: logistic regression is linear and extrapolates linearly; random forest overfits with small leaves
  and is not calibrated; gradient boosting is sensitive to tree size; the network's validation score is
  optimistic because validation chose its stopping epoch.

**Recommendation for the final table:** remove `era` from the model inputs (or map an unseen era to the latest
known one): it adds nothing on validation and its test value cannot be learned.
