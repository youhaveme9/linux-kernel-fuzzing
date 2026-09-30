# Crash triage and fix validation

Use this workflow for a new crash bucket, a reproducer, or a candidate kernel fix.

## Freeze evidence

Stop mutating the affected bucket. Copy it into a new evidence directory and hash its contents:

```sh
python3 scripts/archive_crash.py \
  --workdir /path/to/workdir \
  --bucket CRASH_BUCKET_NAME \
  --output /path/to/evidence/CRASH_BUCKET_NAME
```

Also preserve the manager configuration and log, kernel image, unstripped `vmlinux`, `.config`, source commit, syzkaller commit, VM image identity, and campaign status at discovery time.

## Classify before modifying

Determine whether the event is:

- A kernel memory-safety, locking, lifetime, RCU, refcount, hang, or assertion failure
- A duplicate of an existing bucket with a different surface stack
- An executor, guest-boot, host, storage, or virtualization failure
- Expected noise from deliberately enabled fault injection

Base classification on the complete first report and object lifetime stacks, not only the title.

## Reproduce and minimize

Use the exact crashing kernel first. Confirm the trigger is repeatable and record attempts and successes. Minimize while checking that the same underlying failure remains; a changed title can still be the same bug, and an identical title can hide a different root cause.

Run generated C reproducers in disposable guests. Record privilege, namespaces, timing, and required devices. Do not weaken a host or expose a guest network merely to improve reproduction.

## Validate a fix with matched controls

Build a clean baseline and a clean candidate kernel from the same base and equivalent configuration. Prove the test can fail on the baseline, then run the identical input against the candidate. Check for secondary diagnostics such as reference leaks, unregister waits, lockdep reports, RCU warnings, and delayed timer failures.

Exercise adjacent lifecycle paths, not only the shortest crashing sequence. A lifetime fix should cover normal completion, deletion, expiration, cancellation, timeout, and relevant namespace teardown paths.

## Conclude carefully

A strong result states:

- What reproduced on the baseline
- What did not reproduce on the candidate
- Exact source and artifact identities
- Repetition count and elapsed test window
- Diagnostic classes checked
- Remaining uncertainty

Do not publish a crash, patch, credit line, or security conclusion without the user's explicit approval for that public action.
