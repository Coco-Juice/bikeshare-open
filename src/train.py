"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import json

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


# --- Exercise 4: argue with the result ----------------------------------
# The headline finding is that hgb loses to ridge because trees cannot
# extrapolate the ~65% 2011->2012 growth. These experiments fit a
# TRANSFORMED target and reconstruct predictions back to the cnt scale,
# so they are comparable with the baselines. Experiment code only: it
# prints a table and never writes reports/metrics.json. The committed
# pipeline above remains untransformed.
VARIANTS = {
    # fit on log1p(cnt): relative errors, but the tree's ceiling is
    # exp(log1p(max training cnt)) -- the cap itself is not removed.
    "log1p": {
        "fit_target": "np.log1p(cnt)",
        "reconstruct": "expm1(pred_hat)",
    },
    # fit on log growth vs an observed anchor day, so the tree predicts
    # the CHANGE and the known lag carries the trend level:
    #   y      = log1p(cnt) - log1p(anchor)
    #   cnt_hat = expm1(log1p(anchor_observed) + y_hat)
    "loggrowth_1": {"anchor": "cnt_lag_1"},
    "loggrowth_7": {"anchor": "cnt_lag_7"},
}


def target_experiment(variant: str, splits: list[str]) -> dict:
    import numpy as np
    from sklearn.base import clone

    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, _, _ = temporal_split(df)
    _, valid, test = temporal_split(df)
    by_split = {"valid": valid, "test": test}
    out = {}
    for mname in ("hgb", "ridge"):
        model = clone(MODELS[mname])
        if variant == "log1p":
            y = np.log1p(train[TARGET])
            predict_cnt = lambda part, pred: np.maximum(np.expm1(pred), 0)
        else:
            anchor = VARIANTS[variant]["anchor"]
            y = np.log1p(train[TARGET]) - np.log1p(train[anchor])
            predict_cnt = lambda part, pred: np.maximum(
                np.expm1(np.log1p(part[anchor]) + pred), 0
            )
        model.fit(train[cols], y)
        for tag in splits:
            part = by_split[tag]
            pred = predict_cnt(part, model.predict(part[cols]))
            out.setdefault(mname, {})[tag] = {
                "r2": round(float(r2_score(part[TARGET], pred)), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
            }
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--experiment",
        choices=sorted(VARIANTS),
        help="Exercise 4: fit on a transformed target and print the "
        "reconstructed comparison. Never writes reports/metrics.json.",
    )
    ap.add_argument(
        "--splits",
        default="valid",
        help="comma-separated splits to score (default: valid only; "
        "test is touched once, at the end).",
    )
    args = ap.parse_args()
    if args.experiment is None:
        res = fit_and_score()
        METRICS.parent.mkdir(parents=True, exist_ok=True)
        METRICS.write_text(json.dumps(res, indent=2))
        print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
    else:
        splits = [s.strip() for s in args.splits.split(",")]
        res = target_experiment(args.experiment, splits)
        print(f"experiment={args.experiment} splits={splits} (metrics.json untouched)")
        print(json.dumps(res, indent=2))
