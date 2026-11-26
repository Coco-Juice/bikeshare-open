"""Stage 1: fetch the raw dataset and assert its shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request

import pandas as pd

from src.config import DATA_URL, EXPECTED_RAW_SHA256, RAW

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)


def check_raw_hash() -> None:
    """Guard exercise 2 fault 4: a Bash `cp` into data/raw/ is invisible to
    the PostToolUse hook, so the recorded hash in src/config.py is the
    permanent catch. Fails loudly at `make data` before any downstream
    stage can consume a doctored file."""
    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
    if actual != EXPECTED_RAW_SHA256:
        raise ValueError(
            f"raw data hash mismatch: {RAW.name} is {actual}, expected "
            f"{EXPECTED_RAW_SHA256}. The raw file changed outside the "
            f"pipeline -- this is the fault the hook cannot see. Restore "
            f"with: git checkout -- {RAW.relative_to(RAW.parents[2])}"
        )


def load_raw() -> pd.DataFrame:
    check_raw_hash()
    df = pd.read_csv(RAW, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
