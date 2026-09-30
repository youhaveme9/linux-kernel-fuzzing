# Linux Kernel Fuzzing skill

A Codex skill for auditing, improving, and triaging authorized Linux kernel syzkaller campaigns.

It helps Codex preserve campaign identity, distinguish infrastructure failures from kernel bugs, design one-variable coverage experiments, archive crash evidence, and validate fixes with matched baseline and patched kernels.

## Install

Clone this repository into the Codex skills directory:

```sh
git clone REPOSITORY_URL ~/.codex/skills/linux-kernel-fuzzing
```

Restart or reload Codex so the skill catalog is refreshed.

## Example prompts

```text
Use $linux-kernel-fuzzing to audit this authorized syzkaller campaign read-only.
```

```text
Use $linux-kernel-fuzzing to identify why target-file coverage plateaued and propose one isolated experiment.
```

```text
Use $linux-kernel-fuzzing to preserve and triage this new crash bucket. Do not publish anything.
```

## Helpers

Collect a read-only campaign snapshot:

```sh
python3 scripts/syz_campaign_status.py \
  --config /path/to/manager.cfg \
  --log /path/to/manager.log \
  --manager-pid-file /path/to/manager.pid
```

Archive a crash bucket without changing its source:

```sh
python3 scripts/archive_crash.py \
  --workdir /path/to/workdir \
  --bucket BUCKET_NAME \
  --output /path/to/evidence/BUCKET_NAME
```

Run the test suite:

```sh
python3 -m unittest discover -s tests -v
```

## Safety and scope

This project is for authorized, defensive kernel testing. It does not grant permission to access systems, disclose private findings, contact maintainers, or develop exploits. Credentials and private crash artifacts should never be committed.

## License

MIT
