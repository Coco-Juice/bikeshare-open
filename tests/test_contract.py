"""Guard rails on the ingest contract and the trained model's behaviour."""
import hashlib

import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import (
    EXPECTED_RAW_SHA256,
    FORBIDDEN,
    LAG_WARMUP,
    MODEL_FEATURES,
    RAW,
    TARGET,
)
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_raw_matches_recorded_hash():
    """The named catch for exercise 2 fault 4 (Bash `cp` into data/raw/,
    which the PostToolUse hook cannot see): the raw file must be
    byte-identical to the git-committed original recorded in
    src/config.py. Asserting the hash directly -- rather than only
    exercising it inside load_raw() -- makes the guard itself the red
    test, whatever corrupts the file."""
    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert actual == EXPECTED_RAW_SHA256, (
        f"raw file changed: sha256 {actual} != recorded "
        f"{EXPECTED_RAW_SHA256}. Restore: git checkout -- data/raw/bike_daily.csv"
    )


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_every_model_column_is_classified(feats):
    """No numeric column may reach the modelling table unclassified.

    A new raw column, or an existing leaked one renamed to something
    innocent, flows into feature_columns() unchecked today: the
    exclusion gate only knows FORBIDDEN by name, so `casual_clone`
    sails through while looking nothing like `casual`. The gate this
    test enforces is classification, not name-matching: every numeric
    column in the feature table must be registered in src/config.py --
    excluded (FORBIDDEN and its groups) or explicitly allowed
    (MODEL_FEATURES). New ingestion means new classification, in the
    one file constants live in.
    """
    numeric = set(feats.select_dtypes(include="number").columns)
    unclassified = numeric - set(FORBIDDEN) - set(MODEL_FEATURES)
    assert not unclassified, (
        f"unclassified columns in the modelling table: {sorted(unclassified)}"
    )


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
