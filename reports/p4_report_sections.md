# Report sections from Part 4 (models, metrics, XAI, limitations)

Source of every number: `notebooks/p4_models.ipynb` (sections 4.1-4.13), run on P3's current modeling table
(20 numeric features in 6 groups, train 2006-2019, validation 2020-2021, test 2022-2024). The models use 19 of
them: `era_ordinal` is left out because its test value (3, ground effect) never occurs in the training years
(0-2) and validation is all era 2, so the model would extrapolate without any way to check it (validation
PR-AUC 0.7376 without it, 0.7371 with it).

## 1. Models

All models use the same table, the same 19 features and one shared preprocessing pipeline, fitted on the
training years only: keep the 19 columns, median imputation with a missing-value flag for each feature that has
gaps in the training years (the championship position is empty in round 1, the qualifying gap when no lap was
timed), then standardization. P3's preprocessing experiments and ablation use the same steps without the flags,
which is why P3's logistic-regression baseline and ours differ slightly.

| Model | How it works (one sentence) | Settings after tuning on validation |
|---|---|---|
| Rule `grid <= 3` (baseline) | Predicts a podium for the three cars that start at the front. | none |
| Logistic regression (baseline, **final**) | Weighted sum of the features turned into a probability by the sigmoid. | `C=0.1` |
| Random forest | Average vote of 300 trees, each trained on random rows and features. | `max_features="sqrt"`, `min_samples_leaf=20`, balanced classes |
| Gradient boosting | Small trees built one after another, each correcting the previous ones. | `learning_rate=0.03`, `max_leaf_nodes=7`, 100 trees, balanced classes |
| Shallow neural network (PyTorch) | Two hidden layers (64 and 32 units) with ReLU and dropout 0.2, early stopping on the validation loss. | `pos_weight` for the imbalance, fixed seed and one CPU thread for reproducibility |

Eighteen modeling attempts, each in its own notebook cell with its result: rule, logistic regression (plain, with
`era_ordinal`, balanced, 4 draft features), random forest, gradient boosting, two other families (k-NN 0.677 and
Naive Bayes 0.292 validation PR-AUC, both far behind), four networks (32; 64-32; one wide layer of 128; three
layers 128-64-32), one tuning grid per model, and a number-of-trees study.

**Exploration results (validation PR-AUC):**
* **Network size does not matter here:** 32 units 0.745, 64-32 0.754, 128 units 0.737, three layers 0.744. The
  wider network (4x the weights) and the deeper one (15x the weights of the 32-unit network) are not better, and
  the deeper one starts to overfit after epoch 18. All four are within 0.017, less than the noise (SE 0.038).
* **Number of trees:** a random forest stays flat after about 200 trees (more trees only steady the average);
  gradient boosting peaks at 200 trees (0.746) and then overfits (train 0.86 vs validation 0.72 at 800 trees).
  The tuned models were not changed: the +0.010 at 200 trees is a quarter of the noise level.
* **Naive Bayes fails** because it assumes independent features while grid, qualifying and gap to pole say the
  same thing; **k-NN** weighs all features equally when it looks for similar races.

## 2. Metric choice

* **Primary metric: PR-AUC** (average precision). Podiums are about 15% of rows; PR-AUC measures how well the
  real podium finishers are ranked at the top, needs no threshold, and its floor is the podium rate (0.151),
  not 0.5. A model that always says "no podium" has 84.9% accuracy, which is why accuracy is not used.
* **Secondary metric: F1** at a threshold chosen on validation (highest F1 between 0.05 and 0.95).
* ROC-AUC, precision and recall are reported for completeness.
* **Final model choice (validation only):** the bootstrap standard error of the validation PR-AUC is 0.038;
  all four tuned models are within one standard error of the best (network, 0.754), so the
  one-standard-error rule picks the simplest: **logistic regression, threshold 0.42**. F1 is almost flat between
  thresholds 0.3 and 0.45 (0.70-0.71), so the exact threshold is not important.

## 3. Comparison table (PR-AUC / F1, threshold from validation)

| Model | Train | Validation | Test (unseen) |
|---|---|---|---|
| Rule `grid <= 3` | 0.4863 / 0.6625 | 0.5299 / 0.6953 | 0.4740 / 0.6486 |
| **Logistic regression (final)** | 0.6963 / 0.6687 | 0.7406 / 0.7105 | **0.7018 / 0.6728** |
| Random forest | 0.7888 / 0.7002 | 0.7387 / 0.7176 | 0.6850 / 0.6798 |
| Gradient boosting | 0.7179 / 0.6906 | 0.7364 / 0.7393 | 0.6735 / 0.6695 |
| Neural network | 0.7225 / 0.6976 | 0.7539 / 0.7243 | 0.6880 / 0.6695 |

* P3's features add real information: the same logistic regression reaches validation PR-AUC 0.673 with the
  4 draft features and 0.738 with the 19 features.
* On the test set the final model has the **best PR-AUC** (0.702; ROC-AUC 0.932; no-skill floor 0.151). F1 is a
  tie (random forest 0.680, final model 0.673), well inside the noise; switching models after seeing the test
  set would be a test-set choice, so we did not. The final model finds 146 of the 204 podiums (recall 0.72) with
  84 false alarms (precision 0.63).
* The one-standard-error rule paid off: the network, best on validation (0.754), drops most on test (0.688; its
  stopping epoch was chosen on validation); the simplest model drops least (0.741 to 0.702).
* **Honest note on the test set:** this part was run on three versions of P3's table: (1) 18 features with a
  one-hot `era`, where the test probabilities were pushed up (about 5 predicted podiums per race) because the
  test era never occurs in training; P3 then removed `era`; (2) 17 features from 2003 (test PR-AUC 0.711,
  F1 0.683); (3) the current table, from 2006, 20 features, 19 used (test PR-AUC 0.702, F1 0.673). The feature
  table is P3's, with reasons documented on training and validation years; our exclusion of `era_ordinal` is
  justified without test labels. The models, hyperparameter grids, threshold rule and final-model rule are the
  same in every run, and every choice is made on validation.

## 4. Explainability (XAI)

* **Permutation importance (validation PR-AUC drop):** `grid_fixed` 0.123, `qual_position` 0.108,
  `pos_before` 0.061, all others below 0.03. Per feature group (shuffled together): qualifying 0.189, driver
  standings 0.152, grid 0.129, context 0.010, circuit 0.006, constructor standings 0.002. P3's ablation
  (retraining without each group) gives the same top three with much smaller drops, because a retrained model can
  lean on the remaining correlated features.
* **SHAP:** a position nearer the front (grid, qualifying, championship) and more points before the race push the
  probability up. The team's earlier starts (down) and podiums (up) at the circuit act as a pair, a success rate.
* **Local examples:** Hamilton, Bahrain 2020 (pole, won): baseline 0.175, qualifying P1 +0.19, grid 1 +0.16,
  championship leader +0.15, 307 points +0.14 -> 0.899. Tsunoda, United States 2021 (grid 10, finished 9th):
  -> 0.014. LIME agrees on the direction but approximates poorly (0.29 vs 0.90, R^2 0.43); SHAP adds up exactly.
* **Most confident miss:** Hamilton, Italy 2020: pole, 86.1%, finished 7th after an in-race penalty.
* **Not causal:** the explanations describe how the model uses the features, not what causes a podium. A fast
  car and driver cause both the good starting position and the podium; the model uses the position as a signal.

## 5. Model limitations

* **Slightly high test probabilities:** 3.04 and 3.08 predicted podiums per race on train and validation, 3.32 on
  test. A label-free drift check shows why: the points features grew (average `pts_before` 58.8 in 2022-2024 vs
  36.4 in training; more races and sprint races), so every test driver looks slightly stronger. Ranking is not
  hurt, but a fixed threshold says "podium" a little too often. A points feature relative to the leader would be
  more stable across eras (feature owner's decision).
* **Era sensitivity:** test PR-AUC per season 0.699 (2022), 0.754 (2023, one dominant team), 0.643 (2024, four
  winning teams): how competitive a season is matters as much as the technical era. `era_ordinal` cannot be a
  model input because its test value never occurs in training.
* Qualifying coverage: the table starts in 2006, the first season of today's knockout qualifying.
* Missing values carry meaning: a missing qualifying time in training almost always means a driver who set no
  time, so a pole-sitter with a data gap drops from 72% to 6%; predictions for incomplete records are unreliable.
* Features that are never missing in training (for example `grid_fixed`) have no missing-value flag; if one is
  missing in a new record it is silently replaced by the median, so such a record should be treated as invalid.
* `best_qual_s` depends on the circuit length (only comparable within a race).
* Small validation set (117 podiums, PR-AUC standard error 0.038): the ranking of the tuned models is uncertain.
* The threshold maximizes F1, i.e. treats missed podiums and false alarms as equally bad.
* In-race events (incidents, penalties, safety cars, weather, strategy) cannot be predicted before the race:
  25% of the test false alarms did not finish the race, against 14% of all starters.
* Per model: logistic regression is linear and extrapolates linearly (drifting features shift it); random forest
  overfits with small leaves and is not calibrated; gradient boosting is sensitive to tree size and number of
  trees; the network's validation score is optimistic because validation chose its stopping epoch.

## 6. Hand-off to the inference function (P1)

`FINAL_NAME = "logistic regression"`, `FINAL_THRESHOLD = 0.42`. `FINAL_MODEL` is one pipeline (column
selection + preprocessing + model) that takes the columns of P3's `FEATURES` (20) and uses 19 of them:
`FINAL_MODEL.predict_proba(record[FEATURES])[:, 1]`. Check in 4.13: a complete record (pole-sitter) gives 0.724;
the same record without qualifying and championship position gives 0.062, without an error. P1's checks
(5.4) match the model on all 774 validation rows (largest difference 4e-16). P1's Example B still selects rows
with `driver_form5`, which P3's current table no longer has, so that cell needs P1's update.
