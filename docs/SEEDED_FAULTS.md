# Seeded Faults

## Fault 1: Forbidden casual column

Exact change: Modified feature_columns() to allow the forbidden column casual using or c == "casual".

Reason: casual + registered == cnt, causing target leakage.

Detection: The PostToolUse hook reported a failed leakage test.

Repair: Restored the exclusion condition. All 15 tests passed.

Agent repair turns: 1

### Actual failing pytest output

.F......                                                                 [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.77s


### Hook output (saved excerpt, not complete stderr)

PostToolUse:Edit hook reported a problem
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/kylek/dsc180a-agentic-fresh/bikeshare-open/src/features.py:

E       AssertionError: forbidden columns in feature set: {'casual'}

tests/test_leakage.py:31: AssertionError

1 failed, 7 passed in 1.77s


## Fault 2: Rolling mean includes today

Exact change: Removed .shift(1) from the cnt_roll_7 calculation in src/features.py.

Original: out[TARGET].shift(1).rolling(LAG_WARMUP).mean()

Faulty: out[TARGET].rolling(LAG_WARMUP).mean()

Reason: The faulty rolling mean includes the current day target, introducing leakage.

Detection: test_rolling_mean_excludes_today failed. Obtained 4389.0; expected 4414.857142857143.

Repair: Restored .shift(1) before rolling.

Agent repair turns: 1

### Actual failing pytest output

.....F..                                                                 [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1531.428571
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:67: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.69s


### Hook stderr

Captured excerpt from Claude Code (streams not separately identified):

PostToolUse:Edit hook reported a problem
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing
/home/kylek/dsc180a-agentic-fresh/bikeshare-open/src/features.py:
[714 rows x 29 columns]
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486
tests/test_leakage.py:67: AssertionError
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
1 failed, 7 passed in 1.32s



## Fault 3: Disabled weather encoder validation

Exact change: Replaced if unknown: with if False and unknown: in src/features.py.

Why: Unknown weather labels could be silently converted to NaN instead of raising ValueError.

Initial detection: The original hook did not report a failure because the weather validation test was in tests/test_contract.py, outside the hook test suite.

Additional verification: Added test_weather_encoder_guard_survives to tests/test_leakage.py. A subsequent Claude Edit triggered the hook, which detected the disabled validation.

Repair: Restored if unknown: and removed the temporary comment. All 17 tests passed.

Agent repair turns: 1

### Actual failing pytest output

........F                                                                [100%]
=================================== FAILURES ===================================
_____________________ test_weather_encoder_guard_survives ______________________

    def test_weather_encoder_guard_survives():
        from src.features import encode_weather
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:81: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_guard_survives - Failed: D...
1 failed, 8 passed in 1.42s

### Hook output (captured excerpt, not complete stderr)

PostToolUse:Edit hook reported a problem
[${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /home/kylek/dsc180a-agentic-fresh/bikeshare-open/src/features.py:
........F [100%]
FAILED tests/test_leakage.py::test_weather_encoder_guard_survives - Failed: DID NOT RAISE ValueError
1 failed, 8 passed in 0.83s


## Fault 4: Bash modification of raw data

### Attempt through Claude Code

Command: cp ../fault4-source.txt data/raw/fault4-proof.txt

Actual result: Permission to use Bash with command cp ../fault4-source.txt data/raw/fault4-proof.txt has been denied.

The command never executed. No PostToolUse leakage hook output appeared because the tool call was denied before execution.

### Direct WSL experiment

The same cp command succeeded when executed directly in WSL.

Actual output from cat data/raw/fault4-proof.txt:

Fault 4 permission test

The original bike_daily.csv SHA-256 was:

a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc

The temporary proof file was removed after verification.

### Interpretation and safeguards

The Edit/Write PostToolUse hook does not monitor ordinary WSL terminal commands. The Claude Code Bash attempt was blocked by the permission layer, not the leakage hook. Therefore, this experiment does not establish a successful Claude Code Bash bypass.

A filesystem write restriction, a PreToolUse Bash check, or a raw-data hash check in make data could provide additional protection. No additional safeguard was implemented during this experiment.
