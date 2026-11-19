"""Experiment: HGB on cnt - cnt_lag_1, reconstructed by adding cnt_lag_1.

Train on 2011, evaluate on H1 2012 validation only. The test split returned
by temporal_split is discarded and never used. Does not write metrics.json.

Run: python -m experiments.target_difference
"""
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import PROCESSED, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split


def main() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, _ = temporal_split(df)  # test intentionally unused
    y_valid = valid[TARGET]

    preds = {}
    for name in ("baseline_persistence", "ridge", "hgb"):
        m = clone(MODELS[name]).fit(train[cols], train[TARGET])
        preds[name] = m.predict(valid[cols])

    diff_model = clone(MODELS["hgb"]).fit(
        train[cols], train[TARGET] - train["cnt_lag_1"]
    )
    recon = diff_model.predict(valid[cols]) + valid["cnt_lag_1"].to_numpy()
    preds["hgb_difference"] = recon

    results = {
        n: {
            "r2": round(float(r2_score(y_valid, p)), 4),
            "mae": round(float(mean_absolute_error(y_valid, p)), 1),
        }
        for n, p in preds.items()
    }
    n_neg = int((recon < 0).sum())
    results["_negative_reconstructed"] = {
        "count": n_neg,
        "of": len(recon),
        "min_pred": round(float(recon.min()), 1),
    }
    return results


if __name__ == "__main__":
    res = main()
    print("split: valid (H1 2012) only")
    for k, v in res.items():
        print(f"  {k}: {v}")
    n = res["_negative_reconstructed"]
    print(f"OK target_difference: negative reconstructed counts = {n['count']}/{n['of']}")
