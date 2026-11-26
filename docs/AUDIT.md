# Audit (Exercise 3)

## 1. The repository audited

- **Teammate repo: not audited.** No teammate repository was made
  available before submission, so no `/leakage-auditor` run against a
  teammate's repo is reported here, and no teammate findings are claimed.
- Self-audit repo (for the `agent/audit.py` half): this repository,
  `/home/tonyb/bikeshare-open`.

## 2. The `/leakage-auditor` output, verbatim

**Teammate run: none** (see section 1). The self-audit below uses the
batch harness `agent/audit.py`, which drives the identical reviewer
prompt, tools, and output schema as the `/leakage-auditor` subagent --
only the harness differs (watched single run vs unattended batch row).

Self-audit run (`agent/audit.py`, the batch harness driving the same
reviewer logic; found nothing, run shown as required):

```
$ AUDIT_MODEL=glm-5.3-flash .venv/bin/python agent/audit.py . --out reports/audit.jsonl
[claude-code:unrecognized_model] {"model":"glm-5.3-flash","query_source":"sdk"}
audited 1 repos; 0 flagged -> reports/audit.jsonl
```

(The first attempt failed with the script default `AUDIT_MODEL=bikeshare-coder`
-- `[claude-code:unrecognized_model]` -- because this project's settings
override points at the hosted endpoint where that local model does not
exist. The override above is the setup recorded in README.md's hosted-model
section.)

Result row from `reports/audit.jsonl`, verbatim:

```json
{"repo": "/home/tonyb/bikeshare-open", "confidence": "high", "findings": [{"file": "src/features.py", "issue": "Same-day weather (temp, hum, windspeed, weather_severity) is treated as available at prediction time; this assumes the forecaster knows the day's weather, not just the day's date.", "line": 69, "why_it_matters": "Not target leakage (check_identity is clean and it is disclosed in the code comment), but the valid/test R^2 numbers are conditional on this input-availability assumption; a pure day-ahead forecast without same-day weather would score lower."}, {"file": "src/train.py", "issue": "Uncommitted experiment code (target-transform variants) sits in the working tree on top of the committed pipeline; it is correctly kept out of fit_and_score and metrics.json, but the audited working tree differs from the last commit.", "line": 96, "why_it_matters": "Minor provenance nit, not a methodology error: the experiment writes nothing (verified), yet committing it would make the committed repo match the audited one exactly."}], "leakage": "none", "temporal_ok": true, "baseline_reported": true, "reproducible": true}
```

## 3. Verdict: which findings change a number

No finding changes a number. The auditor's headline verdicts are clean
(leakage `none`, temporal split valid, baselines reported, pipeline
reproducible, confidence high), and of its two advisory findings, the
first -- same-day weather treated as available at prediction time
(src/features.py:69) -- I agree with, but it qualifies how the reported
R^2 numbers may be *interpreted* (they are conditional on a forecaster
having the day's weather, which src/features.py's comment and REPORT.md
both disclose), it does not move them: with a lagged-weather-only
pipeline the scores would be different, but that is a different, smaller
model, not an error in this one. The second -- uncommitted experiment
code in the audited working tree (src/train.py) -- I also agree with as
a provenance nit only: experiment mode is verified to never write
`reports/metrics.json`, the committed metrics are the untransformed
pipeline, and the pending exercise-4 commit adds precisely the commit
boundary the auditor asks for; nothing is recomputed, so no number moves.
The deterministic `check_identity` tool independently re-confirmed no
subset of columns is an exact linear restatement of `cnt` (max residual
tolerance 1e-6), closing the one finding class that *would* change a
number by definition.
