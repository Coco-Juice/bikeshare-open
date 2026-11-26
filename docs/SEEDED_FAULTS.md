# Seeded faults (Exercise 2)

Method per fault: seed the exact change, capture the PostToolUse hook's
stderr and the red test, then fix and count agent turns to green. All
output below is pasted verbatim from real runs, not paraphrased.

The hook (`.claude/hooks/check_leakage.sh`, unchanged from the starter for
this exercise) runs `pytest tests/test_leakage.py -q` after every
`Edit|Write` into `src/*.py`.

**Refresh (2026-11-25).** The three seedable faults were re-run against
the current test files -- the suite has grown by two tests since this
doc was first written (the fault-3 regression test and the
unclassified-column contract test), which shifted line numbers and the
pass counts in the pasted output. Each fresh run below is marked; the
original run narrative and turn counts from Exercise 2 are preserved
under each. Each refresh followed the authored `/seed-fault` skill:
green confirmed, one edit, verbatim stderr, full-suite red, restore,
`git diff` clean.

---

## Fault 1: a forbidden column added to `feature_columns`

**Exact change** (`src/features.py`, `feature_columns`):

```python
return [c for c in numeric if c not in FORBIDDEN or c == "casual"]
```

**Fresh hook stderr (2026-11-25 refresh)** -- arrived in the same turn
as the seeding edit:

```
feats =         dteday  instant  season      yr mnth  ... weather_severity cnt_lag_1  cnt_lag_7   cnt_roll_7  cnt_roll_14
0   ...31.0  WINTER  2012.0  DEC  ...              1.0    1796.0      920.0  1531.428571  2672.571429

[700 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_14', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=============================================== short test summary info ================================================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 8 passed in 0.44s
```

Full suite, red output captured by hand for the record:

```
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 1.32s
```

**Turns to fix: 2** (refresh run; the original 2026-11-19 exercise run
was also 2: hook stderr on the seeding turn, one reverting edit to
green at `15 passed`).

*Note recorded on the original run:* the very first seeding attempt had
produced a hook that exited with ``line 22: python: command not found``
because the session had started before the project venv was activated;
the fault went unnoticed by the hook until the session env resolved
`python`. A hook whose interpreter is missing degrades to *no guard at
all*, silently.

---

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

**Exact change** (`src/features.py`):

```python
out["cnt_roll_7"] = out[TARGET].rolling(7).mean()   # shift(1) removed
```

**Fresh hook stderr (2026-11-25 refresh)** -- in the same turn as the
seeding edit:

```
    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
E             
E             comparison failed
E             Obtained: 4389.428571428572
E             Expected: 4240.714285714285 ± 0.00424071

tests/test_leakage.py:68: AssertionError
=============================================== short test summary info ================================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.428571428572) == 4240.7142857...
1 failed, 8 passed in 0.66s
```

The 149-ride discrepancy at 2011-08-20 is exactly today's count being
pulled into its own 7-day window. Full suite, captured by hand:

```
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.73s
```

**Turns to fix: 2** (refresh run; matching the original run's 2).

---

## Fault 3: the weather encoder's `raise` removed

**Exact change** (`src/features.py`, `encode_weather`) -- the
`if unknown:` block deleted:

```python
    known = series.dropna()
    unknown = set(known.unique()) - set(WEATHER_ORDER)
    return series.map(WEATHER_ORDER).astype(float)   # raise removed
```

### The original run (2026-11-19): an invisible fault

**Hook stderr: none. The hook ran and stayed silent.** Removing the
raise changes nothing today -- every label in the raw file is already
GOOD/MISTY/BAD -- so the guard was latent, and the hook's test selection
never looked at anything that could fail. Full suite for the record:

```
$ python -m pytest -q
...............                                                          [100%]
15 passed in 2.10s
```

**Harm demonstrated in-memory** (no writes to `data/raw/`): one unknown
label planted on 2011-10-31, `build_features` re-run with the fault
seeded:

```
rows with real labels:            700
rows with one 'FOG' label:        699  (no error, no warning)
the poisoned day silently gone:   2011-10-31 in data: False
```

Same input with the raise restored:

```
with the raise restored, same input raises: ValueError: unmapped weather labels: ['FOG']
```

**Turns to fix: 3**, and the hook contributed nothing: seed turn
(hook silent, suite green), harm-demo turn, restore-plus-new-regression-
test turn (`tests/test_leakage.py::test_weather_encoder_fails_loudly_on_unknown_labels`).

### The refresh run (2026-11-25): the same fault, now caught

The regression test added during the original run turns this fault red
the moment it is seeded. **Fresh hook stderr (2026-11-25)** -- arrived
in the same turn as the seeding edit:

```
    def test_weather_encoder_fails_loudly_on_unknown_labels(feats):
        """Seeded-fault regression (Exercise 2, fault 3): deleting the raise in
        encode_weather() changes nothing today (every raw label is known) and is
        invisible to both the hook and this suite. With a raise-less encoder the
        unknown label maps to NaN and the row is silently deleted downstream --
        demonstrated on 2011-10-31 with a planted 'FOG' label. This keeps the
        encoder loud, so the fault goes red the moment it is seeded."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:41: Failed
=============================================== short test summary info ================================================
FAILED tests/test_leakage.py::test_weather_encoder_fails_loudly_on_unknown_labels - Failed: DID NOT RAISE ValueError
1 failed, 8 passed in 0.42s
```

Full suite: `1 failed, 16 passed in 1.28s`. **Turns to fix: 2**
(hook stderr on the seeding turn; one reverting edit to
`17 passed in 1.28s`, `git diff` clean).

---

## Fault 4: the fault the hook cannot see — `cp` into `data/raw/` from Bash

**Exact change:** a doctored CSV (76 rows, 2012-08-01..2012-10-15, `cnt`
doubled; row count and schema untouched so `load_raw()` asserts stay
green) generated in `/tmp`, then:

```
$ cp /tmp/bike_daily_corrupted.csv data/raw/bike_daily.csv
(Bash completed with no output)
```

**What happened: nothing observable.** No hook fired -- the PostToolUse
matcher is `Edit|Write`, and this change never went through either tool.
No permission prompt gated the *content*, only the tool call (see
below). `reports/metrics.json` was then rewritten silently by a normal
`python -m src.features && python -m src.train`, and the reported
numbers got **better**, not worse -- the direction an iterating agent is
trained to keep:

| metric | before cp | after cp | notes |
|---|---|---|---|
| ridge test R² | 0.6268 | 0.7804 | silently "improved" |
| persistence test R² | 0.5099 | 0.8286 | silently "improved" |
| ridge valid R² | 0.6919 | 0.6919 | byte-identical (corruption sits in the test period) |

One tripwire fired by accident, and only when the suite was run
manually: `casual + registered` no longer equals the doubled `cnt`:

```
tests/test_leakage.py:22: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_leakage_identity_holds - assert np.False_
1 failed, 8 passed in 0.41s
```

That is luck, not defense: a corruption scaled across `cnt`, `casual`,
and `registered` together -- or one that never enters the repo's CSV at
all -- passes the entire suite.

**Also observed:** when the same write was attempted through the Bash
*tool*, the session's permission layer refused it twice:

```
Permission to use Bash with command cp /tmp/bike_daily_corrupted.csv data/raw/bike_daily.csv has been denied.
```

The fault only landed because a human executed it directly in the
terminal -- the permission system, not the hook, was the layer that
actually noticed the repo-bound write.

**What would have caught it, permanently:**

1. `data/raw/` is checked into git -- the change was visible immediately
   in `git status`:

   ```
   M data/raw/bike_daily.csv
   ```

2. A raw-data contract test (fixture asserting the file's hash/content
   against its git blob, or pinned knowns: 728 rows, 2011-01-03..2012-12-31,
   2011-03-10 absent) -- none exists today; `src/ingest.py` only checks
   `>= 700 rows` and required column names.
3. A `PreToolUse` deny for Bash writes into `data/raw/**`.
   `.claude/settings.json` denies `Write(./data/raw/**)` and
   `Edit(./data/raw/**)`, but those are *tool* matchers -- Bash is a
   different surface and is not covered.

**Restoration:** `cp /tmp/bike_daily_ORIGINAL.csv data/raw/bike_daily.csv`,
verified byte-identical, and the pipeline rebuilt cleanly:

```
d9b73e6e892a9115bc61a58a81eaeb3e  data/raw/bike_daily.csv
d9b73e6e892a9115bc61a58a81eaeb3e  /tmp/bike_daily_ORIGINAL.csv
-- git sees no change: raw restored --
```

### The guard, implemented (2026-11-25)

Of the three named catches, option 2 -- the hash check -- is implemented:
the committed file's SHA-256 is recorded in `src/config.py`
(`EXPECTED_RAW_SHA256`), `src/ingest.py::check_raw_hash()` verifies it
inside `load_raw()` (so `make data` fails loudly *before* any downstream
stage consumes a doctored file), and
`tests/test_contract.py::test_raw_matches_recorded_hash` asserts the
same recorded hash directly, making the guard itself a red test.

The demonstration: the same corruption as above, re-seeded from
`/tmp`, then `make data` and the suite:

```
$ python -m src.ingest
ValueError: raw data hash mismatch: bike_daily.csv is
6ab12a2ed1c87fd30c9bf8729ebed1a1cb4215f523b6aaa6893b2578d427396d,
expected a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc.
The raw file changed outside the pipeline -- this is the fault the hook
cannot see. Restore with: git checkout -- data/raw/bike_daily.csv

$ python -m pytest -q
1 failed, 1 passed, 16 errors in 1.20s     # test_raw_matches_recorded_hash red, fixtures error at load_raw

$ git checkout -- data/raw/bike_daily.csv   # the guard's own one-command remediation
$ python -m pytest -q
18 passed in 1.25s
```

The diff (summarised; `git show` for full):

```diff
 src/config.py      | EXPECTED_RAW_SHA256 = "a6bed157...5ad9dc"  (recorded hash)
 src/ingest.py      | +check_raw_hash(): sha256(RAW) != EXPECTED -> ValueError with restore instruction
                    | +check_raw_hash() called at the top of load_raw()
 tests/test_contract.py | +test_raw_matches_recorded_hash(): asserts the same recorded hash,
                        |   message carries the restore command
```

What this changes for the original run's story: the permission denial
that blocked the *tool*-mediated `cp` (above) was the only catch before;
now the guard catches the Bash write the hook cannot see, at every
pipeline entry point, with a remediation one-liner -- and a corruption
`cnt`/`casual`/`registered`-together can no longer sneak past the suite,
because the hash test fails first.

---

## Summary

| fault | hook fired? | red test | turns to fix |
|---|---|---|---|
| 1. `casual` in `feature_columns` | yes, same turn (both runs) | `test_no_forbidden_features` | 2 |
| 2. `shift(1)` deleted from `cnt_roll_7` | yes, same turn (both runs) | `test_rolling_mean_excludes_today` | 2 |
| 3. encoder `raise` removed | **no, original run** / **yes after the regression test** | none existed initially; new test added, fault red on refresh | 3 original / 2 refresh |
| 4. Bash `cp` into `data/raw/` | **cannot** (matcher is tool-scoped) | none originally; guard implemented: `test_raw_matches_recorded_hash` red, `make data` fails loudly | n/a (fault + restore executed by the human) |
