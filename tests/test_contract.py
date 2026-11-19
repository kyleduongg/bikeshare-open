"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import LAG_WARMUP, TARGET
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS


def test_weather_encoder_rejects_unknown_labels():
    import pandas as pd
    import pytest
    from src.features import encode_weather
    with pytest.raises(ValueError, match="unmapped weather labels"):
        encode_weather(pd.Series(["GOOD", "UNEXPECTED"]))


def _unclassified_raw_columns(columns):
    from src.config import FORBIDDEN, RAW_DATE_COL, RAW_INPUT_COLS
    known = FORBIDDEN | RAW_INPUT_COLS | {RAW_DATE_COL}
    return sorted(set(columns) - known)


def test_every_raw_column_is_explicitly_classified():
    """A new raw column must be classified in src/config.py before it can
    flow anywhere near the model; it is never accepted silently."""
    from src.config import RAW
    header = pd.read_csv(RAW, nrows=0).columns
    assert not _unclassified_raw_columns(header), (
        f"unclassified raw columns: {_unclassified_raw_columns(header)}; "
        "classify them in src/config.py"
    )


def test_column_classification_detects_unknown_column(tmp_path):
    """Self-check on a copy of the CSV: the real file is never modified."""
    from src.config import RAW
    copy = tmp_path / "bike_daily.csv"
    df = pd.read_csv(RAW, nrows=5)
    df["synthetic_new_col"] = 1
    df.to_csv(copy, index=False)
    assert _unclassified_raw_columns(pd.read_csv(copy, nrows=0).columns) == [
        "synthetic_new_col"
    ]


def test_column_classes_do_not_overlap():
    from src.config import (FORBIDDEN, LEAKAGE_COLS, RAW_DATE_COL,
                            RAW_INPUT_COLS, REDUNDANT_CALENDAR_COLS)
    assert not FORBIDDEN & RAW_INPUT_COLS
    assert RAW_DATE_COL not in FORBIDDEN | RAW_INPUT_COLS
    assert REDUNDANT_CALENDAR_COLS <= FORBIDDEN
    assert not REDUNDANT_CALENDAR_COLS & LEAKAGE_COLS
