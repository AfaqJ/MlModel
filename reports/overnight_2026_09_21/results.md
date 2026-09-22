# Overnight comparison, 2026-09-21

Model-only scores. `july_exam_fold` = 30% of July suppliers held out of every July-trained variant. `july_all` is a fair exam only for models trained without July (v1.4.1, A). E trained on all of July, so its July numbers are memory, not evidence.

## locked843

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 843 | 77.0% | 91.8% | 40.2% | 11 | 225 | 2 |
| A_diet_old | 843 | 69.2% | 87.7% | 32.3% | 13 | 214 | 7 |
| B_july70 | 843 | 76.6% | 90.9% | 36.5% | 7 | 221 | 2 |
| C_july70_diet | 843 | 68.3% | 86.6% | 34.3% | 10 | 207 | 5 |
| E_julyfull_diet | 843 | 69.2% | 87.1% | 32.1% | 15 | 214 | 5 |
| D_july70_diet_ctx | 843 | 66.0% | 83.8% | 28.7% | 11 | 233 | 10 |

## locked843[model_facing]

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 473 | 69.6% | 87.3% | 38.0% | 10 | 122 | 2 |
| A_diet_old | 473 | 66.2% | 86.5% | 30.9% | 5 | 119 | 4 |
| B_july70 | 473 | 71.0% | 86.5% | 36.6% | 6 | 132 | 2 |
| C_july70_diet | 473 | 66.4% | 85.0% | 33.4% | 6 | 115 | 5 |
| E_julyfull_diet | 473 | 67.9% | 86.7% | 32.4% | 12 | 116 | 3 |
| D_july70_diet_ctx | 473 | 67.2% | 85.6% | 30.7% | 9 | 133 | 8 |

## july_exam_fold

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 130 | 37.7% | 60.0% | 21.5% | 7 | 19 | 7 |
| A_diet_old | 130 | 42.3% | 60.0% | 19.2% | 9 | 19 | 6 |
| B_july70 | 130 | 46.2% | 63.1% | 17.7% | 3 | 11 | 3 |
| C_july70_diet | 130 | 43.9% | 60.8% | 24.6% | 7 | 18 | 4 |
| E_julyfull_diet | 130 | 86.9% | 96.2% | 33.1% | 4 | 25 | 0 |
| D_july70_diet_ctx | 130 | 42.3% | 57.7% | 16.2% | 6 | 16 | 3 |

## july_all

| model | rows | top-1 | top-3 | auto-accepted | auto-accept wrong | >=0.90 lines | >=0.90 wrong |
|---|---|---|---|---|---|---|---|
| v1.4.1 | 499 | 43.7% | 66.3% | 20.2% | 28 | 51 | 8 |
| A_diet_old | 499 | 33.3% | 54.1% | 14.0% | 17 | 49 | 9 |
| B_july70 | 499 | 74.8% | 88.0% | 37.1% | 6 | 87 | 3 |
| C_july70_diet | 499 | 67.9% | 82.8% | 23.4% | 11 | 58 | 4 |
| E_julyfull_diet | 499 | 79.2% | 92.8% | 20.6% | 6 | 61 | 0 |
| D_july70_diet_ctx | 499 | 66.7% | 84.6% | 23.2% | 10 | 70 | 4 |
