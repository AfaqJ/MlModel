# Overnight comparison, 2026-09-21

Model-only scores. `july_exam_fold` = 30% of July suppliers held out of every July-trained variant. `july_all` is a fair exam only for models trained without July (v1.4.1, A). E trained on all of July, so its July numbers are memory, not evidence.

## locked843

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| A_diet_old | 843 | 69.2% | 87.7% | 32.3% | 13 | 214 | 7 |
| C_july70_diet | 843 | 68.3% | 86.6% | 34.3% | 10 | 207 | 5 |
| E_julyfull_diet | 843 | 69.2% | 87.1% | 32.1% | 15 | 214 | 5 |
| D_july70_diet_ctx | 843 | 66.0% | 83.8% | 28.7% | 11 | 233 | 10 |

## locked843[model_facing]

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| A_diet_old | 473 | 66.2% | 86.5% | 30.9% | 5 | 119 | 4 |
| C_july70_diet | 473 | 66.4% | 85.0% | 33.4% | 6 | 115 | 5 |
| E_julyfull_diet | 473 | 67.9% | 86.7% | 32.4% | 12 | 116 | 3 |
| D_july70_diet_ctx | 473 | 67.2% | 85.6% | 30.7% | 9 | 133 | 8 |

## july_exam_fold

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| A_diet_old | 130 | 42.3% | 60.0% | 19.2% | 9 | 19 | 6 |
| C_july70_diet | 130 | 43.9% | 60.8% | 24.6% | 7 | 18 | 4 |
| E_julyfull_diet | 130 | 86.9% | 96.2% | 33.1% | 4 | 25 | 0 |
| D_july70_diet_ctx | 130 | 42.3% | 57.7% | 16.2% | 6 | 16 | 3 |

## july_all

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| A_diet_old | 499 | 33.3% | 54.1% | 14.0% | 17 | 49 | 9 |
| C_july70_diet | 499 | 67.9% | 82.8% | 23.4% | 11 | 58 | 4 |
| E_julyfull_diet | 499 | 79.2% | 92.8% | 20.6% | 6 | 61 | 0 |
| D_july70_diet_ctx | 499 | 66.7% | 84.6% | 23.2% | 10 | 70 | 4 |

## F_holdout_exam

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 174 | 36.2% | 56.9% | 19.0% | 7 | 16 | 4 |
| B_july70 | 174 | 49.4% | 67.2% | 17.2% | 2 | 8 | 0 |
| F_targeted_fix | 174 | 42.5% | 62.1% | 17.2% | 5 | 9 | 0 |

## F_holdout_exam[august_holdout]

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 57 | 36.8% | 54.4% | 21.1% | 3 | 1 | 0 |
| B_july70 | 57 | 52.6% | 77.2% | 21.1% | 2 | 0 | 0 |
| F_targeted_fix | 57 | 50.9% | 73.7% | 15.8% | 2 | 0 | 0 |

## F_holdout_exam[july_holdout]

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 117 | 35.9% | 58.1% | 17.9% | 4 | 15 | 4 |
| B_july70 | 117 | 47.9% | 62.4% | 15.4% | 0 | 8 | 0 |
| F_targeted_fix | 117 | 38.5% | 56.4% | 17.9% | 3 | 9 | 0 |
