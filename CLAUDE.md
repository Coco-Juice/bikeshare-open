# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make data` - download raw CSV and assert its shape
- `make features` - build `data/processed/features.parquet`
- `make train` - fit models, write `reports/metrics.json`
- `make test` - pytest; run this before claiming anything works
- `make all` - the three pipeline stages in order
- `python -m src.train --experiment loggrowth_1` - transformed-target
  comparison (Exercise 4). Prints and **never** writes
  `reports/metrics.json`; a bare `make train` writes the committed,
  untransformed numbers.

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `src/config.py` lists these and the
  other excluded columns (`cnt_2d_bfr`, raw time indexes) with the reason
  for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag or rolling feature must be built on a gap-free calendar
  index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
  it aggregates. Add a test for it in `tests/test_leakage.py`.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.
- History windows: the longest is 14 days (`cnt_roll_14`), which is what
  `LAG_WARMUP` in `src/config.py` bounds. The 1/7-day lags use **literal
  7s**, not `LAG_WARMUP` -- never parameterize one feature's window off
  it, or raising it silently rebadges other features' windows (caught by
  `test_rolling_mean_excludes_today` in the seeded-fault exercise).

## Skills
- `/new-feature <feature>` - starter skill; failing test first, then the
  feature, validation delta reported honestly.
- `/seed-fault <fault>` - authored for this assignment's fault exercise:
  confirm green, one minimal edit, record the red run in
  `docs/SEEDED_FAULTS.md`, restore. A fault no test or hook detects is a
  finding to record, not to hide.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Modules are runnable: `python -m src.<module>` prints a one-line `OK ...`
  summary.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. Expect it in
  any residual plot.
