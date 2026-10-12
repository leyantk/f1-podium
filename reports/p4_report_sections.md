# Report sections from Part 4 (models, metrics, XAI, limitations)

Source of every number: `notebooks/p4_models.ipynb` (sections 4.1-4.13), run on P3's final modeling table
(17 numeric features in 6 groups, train 2003-2019, validation 2020-2021, test 2022-2024).

## 1. Models

All models use the same table, the same 17 features and one shared preprocessing pipeline, fitted on the
training years only: median imputation with a missing-value flag for each of the 9 features that have gaps in the
training years (standings are empty in round 1, form in a driver's first race), then standardization.
P3's preprocessing experiments and ablation use the same steps without the flags, which is why P3's
logistic-regression baseline (validation PR-AUC 0.7325) and ours (0.7380) differ slightly.

| Model | How it works (one sentence) | Settings after tuning on validation |
|---|---|---|
| Rule `grid <= 3` (baseline) | Predicts a podium for the three cars that start at the front. | none |
| Logistic regression (baseline, **final**) | Weighted sum of the features turned into a probability by the sigmoid. | `C=10` |
| Random forest | Average vote of 300 trees, each trained on random rows and features. | `max_features="sqrt"`, `min_samples_leaf=5`, balanced classes |
| Gradient boosting | Small trees built one after another, each correcting the previous ones. | `learning_rate=0.1`, `max_leaf_nodes=7`, balanced classes |
| Shallow neural network (PyTorch) | One hidden layer (32 units) with ReLU and dropout 0.2, early stopping on the validation loss. | `pos_weight` for the imbalance, fixed seed and one CPU thread for reproducibility |

Twelve modeling attempts, each in its own notebook cell with its result: three baselines (rule, logistic
regression, balanced logistic regression), logistic regression on the 4 draft features, random forest,
gradient boosting, two networks (one and two hidden layers), and one tuning grid per model.

## 2. Metric choice

* **Primary metric: PR-AUC** (average precision). Podiums are about 15% of rows; PR-AUC measures how well the
  real podium finishers are ranked at the top, needs no threshold, and its floor is the podium rate (0.151),
  not 0.5. A model that always says "no podium" has 84.9% accuracy, which is why accuracy is not used.
* **Secondary metric: F1** at a threshold chosen on validation (highest F1 between 0.05 and 0.95).
* ROC-AUC, precision and recall are reported for completeness.
* **Final model choice (validation only):** the bootstrap standard error of the validation PR-AUC is 0.039;
  all four tuned models are within one standard error of the best (network, 0.758), so the
  one-standard-error rule picks the simplest: **logistic regression, threshold 0.23**.

## 3. Comparison table (PR-AUC / F1, threshold from validation)

| Model | Train | Validation | Test (unseen) |
|---|---|---|---|
| Rule `grid <= 3` | 0.4696 / 0.6476 | 0.5299 / 0.6953 | 0.4740 / 0.6486 |
| **Logistic regression (final)** | 0.6907 / 0.6683 | 0.7387 / 0.7132 | **0.7106 / 0.6834** |
| Random forest | 0.9088 / 0.7845 | 0.7290 / 0.7068 | 0.6806 / 0.6680 |
| Gradient boosting | 0.7485 / 0.7019 | 0.7323 / 0.7266 | 0.6850 / 0.6557 |
| Neural network | 0.7081 / 0.6881 | 0.7576 / 0.7250 | 0.7005 / 0.6789 |

* P3's features add real information: the same logistic regression reaches validation PR-AUC 0.672 with the
  4 draft features and 0.738 with the 17 features.
* On the test set the final model is the **best on both chosen metrics** (PR-AUC 0.711, F1 0.683; ROC-AUC 0.936;
  no-skill floor 0.151). It finds 177 of the 204 podiums (recall 0.87) with 137 false alarms (precision 0.56).
* The one-standard-error rule paid off: the network, best on validation (0.758), drops to 0.701 on test
  (its stopping epoch was chosen on validation); the random forest overfits (train 0.909, test 0.681).
* **Honest note on the test set:** the test set was first scored when the table still had 18 features,
  including `era`. That run showed the test-year probabilities pushed upwards (about 5 predicted podiums per race
  instead of 3; F1 0.581, PR-AUC 0.712), because the test era `ground_effect` never occurs in training.
  P3 then removed `era`, a choice justified without the test labels (an unseen category cannot be learned; on
  validation `era` adds nothing: PR-AUC 0.7312 with it, 0.7325 without). The numbers above are for the final
  17 features. Nothing else was changed after looking at the test set: the models, the hyperparameter grids,
  the threshold rule and the final-model rule are the same, and every choice is made on validation.

## 4. Explainability (XAI)

* **Permutation importance (validation PR-AUC drop):** `qual_position` 0.169, `grid` 0.089, all others below
  0.025. Per feature group (shuffled together): qualifying 0.112, grid 0.098, standings 0.057, form 0.028,
  circuit 0.004, context (`home_flag`) -0.003. P3's ablation (retraining without each group) gives a similar
  order with smaller drops, because a retrained model can lean on the remaining correlated features.
* **SHAP:** a position nearer the front (qualifying, grid, championship) and good recent form push the
  probability up. Correlated inputs produce surprising single signs (`reached_q3 = 1` pushes down given the
  exact qualifying position).
* **Local examples:** Hamilton, Bahrain 2020 (pole, won): baseline 0.167, grid +0.21, form +0.16, qualifying
  +0.13, leading the championship +0.10 -> 0.924. Vettel, Qatar 2021 (grid 10, finished 10th): -> 0.017.
  LIME agrees on the direction but approximates poorly (0.34 vs 0.92, R^2 0.53); SHAP adds up exactly.
* **Most confident miss:** Hamilton, Italy 2020: pole, 91.3%, finished 7th after an in-race penalty.
* **Not causal:** the explanations describe how the model uses the features, not what causes a podium. A fast
  car and driver cause both the good starting position and the podium; the model uses the position as a signal.

## 5. Model limitations

* Probabilities are realistic in every split (about 3.0 predicted podiums per race on train, validation and test);
  this label-free check should be repeated for every new season.
* Era sensitivity: rules, cars and the points system change (25 points for a win since 2010, 10 before); the test
  years are a new technical era. The features still transfer (small validation-to-test drop), but a future rule
  change could shift them. `era` itself cannot be a model input because its test value never occurs in training.
* Qualifying coverage: the table starts in 2003 because older qualifying data is missing or in other formats.
* Missing values carry meaning: a missing qualifying time in training almost always means a driver who set no
  time, so a pole-sitter with a data gap gets about 1%; predictions for incomplete records are unreliable.
* Features that are never missing in training (for example `grid`) have no missing-value flag; if one is missing
  in a new record it is silently replaced by the median, so such a record should be treated as invalid input.
* `best_qual_s` depends on the circuit length (only comparable within a race).
* Small validation set (117 podiums, PR-AUC standard error 0.039): the ranking of the tuned models is uncertain.
* The threshold maximizes F1, i.e. treats missed podiums and false alarms as equally bad.
* In-race events (incidents, penalties, safety cars, weather, strategy) cannot be predicted before the race:
  20% of the test false alarms did not finish the race, against 14% of all starters.
* Per model: logistic regression is linear and extrapolates linearly; random forest overfits with small leaves
  and is not calibrated; gradient boosting is sensitive to tree size; the network's validation score is
  optimistic because validation chose its stopping epoch.

## 6. Hand-off to the inference function (P1)

`FINAL_NAME = "logistic regression"`, `FINAL_THRESHOLD = 0.23`, 17 features (`FEATURES` from Part 3).
`FINAL_MODEL` is one pipeline (preprocessing + model): `FINAL_MODEL.predict_proba(record[FEATURES])[:, 1]`.
Check in 4.13: a complete record (pole-sitter) gives 0.758; the same record without qualifying and standings
gives 0.011, without an error.
