# REPORT: Daily Bikeshare Demand Forecasting (Methodology Assignment 7)

Target: `cnt` (total daily rides). Split by date: train = 2011 (348 rows), validation = H1 2012 (182), test = H2 2012 (184). All numbers below are copied from recorded files: `reports/metrics.json`, `../baseline-metrics-before-feature.json` and `../cnt_lag_2-experiment.json`. Nothing was re-run for this report.

## 1. Results

**Two runs, kept distinct.**
- *Before* `cnt_lag_2` is the **final committed pipeline**: 14 features, untransformed target, `reports/metrics.json`. The "before" file `../baseline-metrics-before-feature.json` is identical to it.
- *After* `cnt_lag_2` is an **earlier feature experiment** (`../cnt_lag_2-experiment.json`): 15 features, the 14 above plus `cnt_lag_2`. It was not adopted and is not in the final pipeline. Test metrics for it are recorded, so no values are missing.

| # | Model | cnt_lag_2 | Valid R² | Valid MAE | Test R² | Test MAE |
|---|-------|-----------|---------:|----------:|--------:|---------:|
| 1 | baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| 2 | baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| 3 | baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| 4 | baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| 5 | ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| 6 | ridge | after | 0.6453 | 833.4 | 0.5830 | 945.5 |
| 7 | hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| 8 | hgb | after | 0.2481 | 1269.8 | -0.4737 | 1947.9 |

The two baselines do not use features, so they are unchanged by the new column, as expected.

**Why `cnt_lag_2` was rejected.** I tested `cnt_lag_2`, the count two calendar days earlier. It is known before prediction day and is not target leakage. I rejected it as a model input because Ridge's validation performance worsened slightly (R² 0.6475 → 0.6453) even though HGB improved (0.2185 → 0.2481). HGB was still far below persistence (0.4507), and Ridge, the strongest model, did not benefit, so the feature gave no meaningful improvement. The implementation and its calendar-alignment test remain in the repo for verification. `feature_columns()` explicitly excludes it.

The decision rested on validation. The experiment output also printed test metrics, and I recorded that in `docs/DECISIONS.md`. The test numbers above are reported for completeness and played no part in the choice.

## 2. Headline finding

**The perfect score is invalid.** With `casual` and `registered` as features, a model scores R² ≈ 1.000. This is because `casual + registered == cnt` exactly, so the model is given the answer. `docs/DECISIONS.md` records this as "Leaky model R² 1.000 → honest ridge 0.583". I have no saved metrics file for the leaky run, only that decision line, so I cite it from there. Both columns are excluded through `FORBIDDEN` in `src/config.py`, and `tests/test_leakage.py` guards this.

**Honest test results (final pipeline, H2 2012):**

| Model | Test R² | Test MAE |
|---|---:|---:|
| Ridge | 0.5833 | 947.1 |
| Persistence (yesterday's count) | 0.5099 | 840.1 |
| HGB | -0.4975 | 1972.6 |
| Historical mean | -2.1441 | 2847.7 |

Ridge has the best test R². Persistence is close and has the lower MAE. HGB's R² is negative on test, so it is worse than predicting the test-period mean, yet it still beats the historical (2011) mean baseline, which is far worse because that mean is stale.

**Growth and extrapolation.** Ridership grew about 65% from 2011 to 2012. HGB is trained only on 2011 and a tree can only output values near those it saw in training, so it cannot follow the higher 2012 level. That is why its errors are large (test MAE 1972.6) and its R² is negative. Ridge is linear and uses lag features, so it carries the new level forward. I treat this as the central result, not a bug. Time-index columns (`instant`, `yr`, `days_since_2011`) were excluded so that no model could cheat the trend.

**`cnt_lag_2` was not retained.** The selected feature set is the 14 features listed in `reports/metrics.json`.

## 3. Exercise 4: target transformation

I tested HGB predicting `cnt - cnt_lag_1`, then reconstructing counts by adding `cnt_lag_1` back (`experiments/target_difference.py`). It trains on 2011, evaluates on H1 2012 validation only, discards the test split and writes no metrics file.

| Validation model | R² | MAE |
|---|---:|---:|
| HGB, original (absolute counts) | 0.2185 | 1296.6 |
| HGB, transformed (difference, reconstructed) | 0.6079 | 834.3 |
| Ridge | 0.6475 | 832.9 |

Of the 182 reconstructed validation predictions, none is negative. I did not re-run the script for this report. The transformed HGB figures and the negative-count result come from your recorded numbers and the `DECISIONS.md` entry; the script itself prints the count.

The transformation helps because the model predicts a day-over-day change, which is roughly stationary, and the level comes from `cnt_lag_1`, so the tree no longer needs to extrapolate. I accept it as methodologically defensible for one-day-ahead forecasting, because yesterday's actual count is available at prediction time and no future target information is used. It would not hold for multi-day horizons without yesterday's actual value. A defensible approach does not need to be the best one: Ridge is still slightly better (0.6475 vs 0.6079). **The committed final pipeline remains untransformed.**

## 4. Exercise 5: ridge vs persistence

I chose to deploy Ridge, and the validation evidence supports it. On H1 2012, Ridge scores R² 0.6475 and MAE 832.9, against persistence at R² 0.4507 and MAE 900.6. That is a gain of about 0.20 R² and 68 rides of MAE, and Ridge wins on both measures. Persistence can only repeat yesterday, so it cannot use weather, weekday or holiday information, and it inherits every one-day swing. Ridge uses these signals and also smooths the noise through `cnt_lag_7` and `cnt_roll_7`. Validation exists to make this kind of choice, so selection was made there. In fairness, persistence has the better test MAE (840.1 vs 947.1), and its test R² (0.5099) is within 0.07 of Ridge's (0.5833). I report this as a limitation of the deployment and a reason to monitor live error. I did not use it to change the selection afterwards, because choosing a model by its test score would make the test set a second validation set and the reported test numbers would no longer be an honest estimate. Persistence stays as the simple benchmark Ridge must keep beating.

## 5. Attribution

**Model used.** The agent was hosted Anthropic **Claude Sonnet**. `.claude/settings.json` sets `"model": "sonnet"`, an alias only. The repo does not record a version. The session's system information identifies the model as **Sonnet 5.5, model ID `claude-sonnet-5-5`**. This is what I could confirm. I am not stating a parameter count or context length, because no evidence of either is available.

**Configuration change (disclosed).** The starter used a local Ollama setup: model `bikeshare-coder`, `ANTHROPIC_BASE_URL=http://localhost:11434`, and a dummy `ollama` auth token. Commit `921dd17` ("config: use Claude Sonnet and document model choice") replaced these with `"model": "sonnet"` and removed the three Ollama environment variables. The `DECISIONS.md` entry dated 2026-11-18 confirms it. Hooks, permissions and the verification workflow were kept. `model/` (Modelfile, check.sh) and `agent/audit.py` are unchanged starter files and are not used by the final pipeline. One caveat: the commit history does not show which model made each earlier edit, so I cannot say whether any early work happened under the Ollama configuration.

**Agent-generated files and functions** (identified from commit diffs and the documented workflow; agent contributions are explicitly attributed despite commits using my Git identity):
- `src/features.py`: `cnt_lag_2` construction, and its exclusion in `feature_columns()`.
- `src/config.py`: `REDUNDANT_CALENDAR_COLS`, `RAW_INPUT_COLS`, `RAW_DATE_COL` and updates to the `FORBIDDEN` composition; `LEAKAGE_COLS` originated in the starter.
- `tests/test_leakage.py`: `test_cnt_lag_2_is_two_calendar_days_back`, `test_weather_encoder_guard_survives`.
- `tests/test_contract.py`: `_unclassified_raw_columns`, `test_every_raw_column_is_explicitly_classified`, `test_column_classification_detects_unknown_column`, `test_column_classes_do_not_overlap`.
- `experiments/target_difference.py`: `main()`.
- `.claude/skills/seed-fault/SKILL.md`, and the three seeded-fault runs with their evidence in `docs/SEEDED_FAULTS.md`.
- This `REPORT.md`.

**My methodological decisions** (each cross-checked against `docs/DECISIONS.md`):

| Decision | In DECISIONS.md? |
|---|---|
| Exclude `casual`, `registered` (sum to `cnt`) | Yes |
| Exclude `cnt_2d_bfr` (unverifiable alignment) | Yes |
| Exclude `instant`, `yr`, `days_since_2011` | Yes |
| Date-based 2011 / H1 2012 / H2 2012 split; model selection based on validation results | Yes |
| Report mean and persistence baselines with every score | Yes |
| Choose hosted Sonnet over Ollama | Yes |
| Reject `cnt_lag_2` on validation grounds | Yes |
| Selection based on validation, not test | Yes |
| Exclude `season`, `mnth`, `weekday` as redundant | Yes |
| Name `/seed-fault` in CLAUDE.md (tooling only) | Yes |
| Exercise 4: accept difference target as defensible; keep untransformed final pipeline | Yes |
| Exercise 5: deploy Ridge on validation evidence | Yes |

All twelve claimed decisions have a matching entry.

**Evidence limitations:**
- No saved metrics file exists for the leaky (R² 1.000) run. That figure is cited from `DECISIONS.md` only.
- Transformed-HGB numbers (R² 0.6079, MAE 834.3) were not recomputed here. No metrics file stores them, and none was written by the script.
- The `DECISIONS.md` line for `cnt_lag_2` mentions only validation R², so the validation MAEs for it come from the experiment JSON.
- The exact Sonnet version rests on this session's system information. The repo only has the alias `sonnet`.
- Agent authorship of files is inferred, not logged.

**SDK self-audit findings.** The hosted-Sonnet SDK audit
(`reports/audit.jsonl`) reported no leakage, a valid temporal split,
reported baselines, and reproducibility, with two advisory findings.
First, `cnt_lag_2` is computed but excluded through a hard-coded rule
in `feature_columns()`. This was intentional: I rejected the feature
after its validation results slightly worsened Ridge performance.
I acknowledge that a hard-coded exclusion is less maintainable, but
it does not represent leakage or invalidate the reported metrics.
Second, the auditor noted the lack of a global random seed, although
HGB has `random_state=0` and the other evaluated models are deterministic.
Neither finding requires changing the selected model.
