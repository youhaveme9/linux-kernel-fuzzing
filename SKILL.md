---
name: linux-kernel-fuzzing
description: Audit, improve, and triage authorized Linux kernel syzkaller campaigns. Use for campaign health checks, coverage experiments, corpus changes, crash triage, and matched kernel regression validation.
---

# Linux Kernel Fuzzing

Operate as a careful campaign engineer. Optimize for reproducibility and useful target coverage, not raw execution count.

## Boundaries

- Work only on systems and kernels the user has authorized.
- Treat status and review requests as read-only. Change configurations, restart managers, or mutate corpora only when the request authorizes those actions.
- Never expose credentials, tokens, private reports, or unpublished crash artifacts in logs or generated files.
- Do not publish reports, send email, open issues, or contact maintainers without separate explicit authorization for that public action.
- Do not turn a crash into an exploit. This skill covers defensive reproduction, root-cause analysis, fixes, and regression testing.

## Shared invariants

1. Record the exact kernel commit, patch IDs, config hash, compiler identity, syzkaller commit, image hash, and campaign config before drawing conclusions.
2. Use clean, separate worktrees for baseline and patched kernels. Do not rely on a tree with staged or unrelated changes.
3. Preserve existing corpora, crash buckets, logs, and reports. Use new work directories for experiments and snapshot material evidence before changing state.
4. Compare baseline and candidate runs with equivalent kernel configuration, VM resources, corpus, syscall surface, and reproducer inputs.
5. Change one campaign variable per experiment unless interactions are the explicit subject of the experiment.
6. Separate infrastructure failures from kernel failures. Confirm the guest booted, KCOV works, the executor runs, and the target code is reachable.
7. Treat “no crash found” as bounded evidence, not proof that a bug is absent.

## Choose the workflow

- For current health, configuration review, stalls, or campaign readiness, read [references/campaign-audit.md](references/campaign-audit.md).
- For increasing target coverage or evaluating seeds and syscall descriptions, read [references/coverage-experiments.md](references/coverage-experiments.md).
- For a new crash bucket, reproducer, candidate fix, or baseline-versus-patched result, read [references/crash-triage.md](references/crash-triage.md).

Read only the reference needed for the request.

## Helpers

Use `scripts/syz_campaign_status.py` for a deterministic, read-only snapshot of a local syzkaller campaign. It parses the manager log, scopes process discovery to the supplied config and kernel, and reports crash buckets.

Use `scripts/archive_crash.py` to copy one crash bucket into a new evidence directory with a manifest and SHA256 checksums. The helper refuses to overwrite an existing archive.

## Completion

Report the observed outcome first. Include exact artifacts and commands that support it, relevant limitations, and the safest next experiment. When changes were made, verify the manager, intended guest count, target coverage, corpus activity, and crash state after startup.
