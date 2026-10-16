# Report sections from Part 4 (models, metrics, XAI, limitations)

Source of every number: `notebooks/p4_models.ipynb` (sections 4.1-4.13), run on P3's final modeling table:
12 numeric features in 4 groups (grid, qualifying, driver standings, constructor standings), train 1950-2019
with P3's training weights (`sample_weight`: 0.25 for 1950-2005, 1 from 2006), validation 2020-2021,
test 2022-2024.

## 1. Models

All models use the same table, the same 12 features and one shared preprocessing pipeline, fitted on the
training years only: keep the 12 columns, median imputation with a missing-value flag for each feature that has
gaps in the training years, then standardization. Every model receives P3's training weights (passed to the
model step of the pipeline; the network multiplies each row's loss by its weight), except k-NN, which cannot use
weights and is trained on 2006-2019 only. `train_eval()` (shared with P3 in `src/f1_eval.py`) has an optional
`sample_weight` argument; calls without it behave as before.

| Model | How it works (one sentence) | Settings after tuning on validation |
|---|---|---|
| Rule `grid <= 3` (baseline) | Predicts a podium for the three cars that start at the front. | none |
| Logistic regression (baseline, **final**) | Weighted sum of the features turned into a probability by the sigmoid. | `C=10` |
| Random forest | Average vote of 300 trees, each trained on random rows and features. | `max_features="sqrt"`, `min_samples_leaf=5`, balanced classes |
| Gradient boosting | Small trees built one after another, each correcting the previous ones. | `learning_rate=0.1`, `max_leaf_nodes=7`, 100 trees, no automatic early stopping, balanced classes |
| Shallow neural network (PyTorch) | One hidden layer (128 units) with ReLU and dropout 0.2, early stopping on the validation loss. | weighted loss, `pos_weight` for the imbalance, fixed seed and one CPU thread |

Nineteen modeling attempts, each in its own notebook cell: rule; logistic regression with weights, without
weights and on 2006-2019 only; balanced; 4 draft features; random forest; gradient boosting; two other families
(k-NN and Naive Bayes); four networks (32; 64-32; 128; three layers 128-64-32); one tuning grid per model; and a
number-of-trees study.

**Exploration results (validation PR-AUC):**
* **Training weights:** weighted 0.736, no weights 0.728, 2006-2019 only 0.744. The weights help compared with
  full-weight old seasons; dropping the old seasons is slightly higher, as P3 also found. The team keeps them,
  weighted, on purpose. All three are within the noise (SE about 0.037).
* **Network size does not matter here:** 32 units 0.759, 64-32 0.759, 128 units 0.763, three layers 0.755. The
  deeper network reaches its best epoch at 8 and then starts to overfit. All four are within 0.008.
* **Number of trees:** a random forest stays flat after about 200 trees; gradient boosting peaks at 200 trees
  (0.736) and then overfits (train 0.78 vs validation 0.68 at 800 trees).
* **Other families:** k-NN 0.736 (much better than with 19 features, 0.677, because the short feature list
  contains only strong features), Naive Bayes 0.570 (twin features break its independence assumption).

## 2. Metric choice

* **Primary metric: PR-AUC** (average precision). Podiums are about 15% of rows; PR-AUC measures how well the
  real podium finishers are ranked at the top, needs no threshold, and its floor is the podium rate (0.151),
  not 0.5. A model that always says "no podium" has 84.9% accuracy, which is why accuracy is not used.
* **Secondary metric: F1** at a threshold chosen on validation (highest F1 between 0.05 and 0.95).
* ROC-AUC, precision and recall are reported for completeness. Training scores use the training weights;
  validation and test rows all have weight 1.
* **Final model choice (validation only):** the bootstrap standard error of the validation PR-AUC is 0.037;
  all four tuned models are within one standard error of the best (network, 0.763), so the
  one-standard-error rule picks the simplest: **logistic regression, threshold 0.29**. F1 is almost flat between
  thresholds 0.25 and 0.35 (about 0.71), so the exact threshold is not important.

## 3. Comparison table (PR-AUC / F1, threshold from validation)

| Model | Train (weighted) | Validation | Test (unseen) |
|---|---|---|---|
| Rule `grid <= 3` | 0.4127 / 0.5977 | 0.5299 / 0.6953 | 0.4740 / 0.6486 |
| **Logistic regression (final)** | 0.6254 / 0.6236 | 0.7366 / 0.7099 | **0.6923 / 0.6760** |
| Random forest | 0.8424 / 0.7450 | 0.7401 / 0.7184 | 0.6701 / 0.6564 |
| Gradient boosting | 0.6592 / 0.6361 | 0.7326 / 0.7224 | 0.6818 / 0.6667 |
| Neural network | 0.6460 / 0.6300 | 0.7632 / 0.7356 | 0.6926 / 0.6851 |

* P3's features add real information: the same weighted logistic regression reaches validation PR-AUC 0.667
  with the 4 draft features and 0.736 with the 12 features.
* Training scores are lower than validation because they include the 1950-2005 seasons, which are harder to
  predict (more cars, more retirements, little qualifying data).
* On the test set the final model and the network tie on PR-AUC (0.692 and 0.693; ROC-AUC 0.93; no-skill floor
  0.151); the network has a slightly higher F1 (0.685 vs 0.676), well inside the noise. Switching after seeing
  the test set would be a test-set choice, so we did not. The final model finds 169 of the 204 podiums
  (recall 0.83) with 127 false alarms (precision 0.57).
* The one-standard-error rule held: the network (best on validation, 0.763) and the random forest (0.740) drop
  most on test (to 0.693 and 0.670); the simplest model drops least (0.737 to 0.692).
* Compared with the previous version (19 features, training 2006-2019): test PR-AUC 0.702 then, 0.692 now;
  F1 0.673 then, 0.676 now. Practically the same quality with 12 features instead of 19.
* **Honest note on the test set:** this part was run on four versions of P3's table: (1) 18 features with a
  one-hot `era`, where the test probabilities were pushed up because the test era never occurs in training;
  (2) 17 features from 2003; (3) 20 features from 2006 (19 used); (4) the final 12 features, 1950-2019 with
  weights. Every table change was P3's, with reasons documented on training and validation years. The models,
  hyperparameter grids, threshold rule and final-model rule are the same in every run, and every choice is made
  on validation.

## 4. Explainability (XAI)

* **Permutation importance (validation PR-AUC drop):** `grid_fixed` 0.262, `pts_before` 0.101,
  `gap_to_pole_pct` 0.044, `qual_position` 0.042, the rest below 0.03. Per feature group (shuffled together):
  grid 0.261, driver standings 0.165, qualifying 0.122, constructor standings 0.038. P3's ablation (retraining
  without each group) gives the same top groups with smaller drops, because a retrained model can lean on the
  remaining twin features.
* **SHAP:** a starting slot, qualifying position, gap to pole and championship position nearer the front, and
  more points before the race, push the probability up. Two twin features have counter-intuitive signs (many team
  points and reaching Q3 push slightly down, given the driver's own points and qualifying position).
* **Local examples:** Verstappen, Abu Dhabi 2021 (pole, won): baseline 0.171, 369.5 points +0.37, grid 1 +0.31,
  qualifying P1 +0.11, team points -0.20 -> 0.910. Vettel, French GP 2021 (grid 12, finished 9th): -> 0.016.
  LIME agrees on the direction but approximates poorly (0.33 vs 0.91, R^2 0.50); SHAP adds up exactly.
* **Most confident miss:** Hamilton, Italy 2020: pole, 81.3%, finished 7th after an in-race penalty.
* **Not causal:** the explanations describe how the model uses the features, not what causes a podium. A fast
  car and driver cause both the good starting position and the podium; the model uses the position as a signal.

## 5. Model limitations

* **Probabilities:** median predicted podiums per race 3.09 (1950-2005), 2.93 (2006-2019), 3.02 (validation),
  3.14 (test). The small excess on test comes from points drift: average `pts_before` is 58.8 in 2022-2024 vs
  36.4 in 2006-2019 (more races and sprint races), so every test driver looks slightly stronger.
* **Era sensitivity:** test PR-AUC per season 0.685 (2022, first season of new rules), 0.764 (2023, one dominant
  team), 0.635 (2024, four winning teams).
* **Old seasons:** training on 2006-2019 only scores slightly higher on validation (0.744 vs 0.736, within
  noise); the old seasons are kept with weight 0.25 by team decision (P3, 3.11 Part F).
* Missing values carry meaning: for a modern driver, missing qualifying data is rare and read as a bad sign; a
  pole-sitter without qualifying data and championship position drops from 68% to 8%. Predictions for incomplete
  records are unreliable (P1's inference function refuses incomplete records).
* Features that are never missing in training (for example `grid_fixed`) have no missing-value flag; if one is
  missing in a new record it is silently replaced by the median, so such a record should be treated as invalid.
* Small validation set (117 podiums, PR-AUC standard error 0.037): the ranking of the tuned models is uncertain.
* The threshold maximizes F1, i.e. treats missed podiums and false alarms as equally bad.
* In-race events (incidents, penalties, safety cars, weather, strategy) cannot be predicted before the race:
  20% of the test false alarms did not finish the race, against 14% of all starters.
* Per model: logistic regression is linear and extrapolates linearly (drifting features shift it); random forest
  overfits with small leaves and is not calibrated; gradient boosting is sensitive to the number and size of
  trees; the network's validation score is optimistic because validation chose its stopping epoch; k-NN cannot
  use the training weights; Naive Bayes assumes independent features.

## 6. Hand-off to the inference function (P1)

`FINAL_NAME = "logistic regression"`, `FINAL_THRESHOLD = 0.29`, 12 features (`FEATURES` from Part 3).
`FINAL_MODEL` is one pipeline (column selection + preprocessing + model):
`FINAL_MODEL.predict_proba(record[FEATURES])[:, 1]`. The training weights are used in training only; a
prediction needs no weight. Check in 4.13: a complete record (pole-sitter) gives 0.678; the same record without
qualifying and championship position gives 0.082. P1's inference notebook (latest version, on the P2 branch)
matches the model on all 722 complete validation rows (largest difference 4e-16); some of its messages still say
"17 engineered features".
