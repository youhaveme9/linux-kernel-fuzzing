# Campaign audit

Use this workflow for health checks, readiness reviews, configuration audits, and stalled campaigns.

## Establish identity

Capture before interpreting statistics:

- Kernel repository path, `HEAD`, cleanliness, and image hash
- Kernel `.config` hash and relevant instrumentation such as KCOV, KASAN, lock debugging, and the target subsystem
- Syzkaller repository path, commit, and cleanliness
- Manager configuration and hash
- Work directory, corpus database hash, VM image hash, and SSH key path without reading the key
- Manager PID, start time, guest count, dashboard address, and log path

If source identity is ambiguous, stop the audit conclusion and resolve it. A running campaign against the wrong image is not useful evidence.

## Collect a snapshot

When the campaign is local to the execution environment, run:

```sh
python3 scripts/syz_campaign_status.py \
  --config /path/to/manager.cfg \
  --log /path/to/manager.log \
  --manager-pid-file /path/to/manager.pid
```

Use `--json` for an artifact that another tool will compare. The helper is read-only.

Also inspect the manager's machine-check output. Confirm:

- Coverage and the intended sandbox are enabled
- The executor and network injection work when required
- Requested syscalls were not transitively disabled
- The coverage focus resolves to the intended source files
- Guest churn is not hiding boot failures

Optional subsystem warnings are not automatically campaign failures. Explain why a warning is irrelevant before discounting it.

## Judge health from deltas

A single snapshot shows state, not progress. Compare at least two timestamped snapshots and calculate:

- Executions and execution-rate trend
- Total corpus growth
- Target-focused corpus growth
- Overall and target-file coverage growth
- New crash buckets and reproduction activity
- Guest restarts, manager restarts, and host resource pressure

Do not call a campaign “stalled” from elapsed time alone. A plateau is meaningful when target coverage and useful corpus growth remain flat across an appropriate observation window while execution continues normally.

## Readiness gate

Before a long run, require:

1. A clean source identity and reproducible build record.
2. A smoke test proving every configured guest can boot and execute programs.
3. Seed corpus integrity and a fresh experiment work directory.
4. Evidence that the target file or functions receive coverage.
5. A known-positive control when validating a bug fix.
6. A notification or monitoring path that watches the actual campaign directory.

## Report format

Lead with one of: healthy, degraded, stalled, crashed, or identity uncertain. Then give the evidence, limitations, and one recommended next action. Avoid implying that zero crashes proves correctness.
