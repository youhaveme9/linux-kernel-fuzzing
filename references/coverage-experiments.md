# Coverage experiments

Use this workflow when improving reachability, seeds, syscall descriptions, focus areas, timing, or corpus quality.

## Form a testable hypothesis

Tie an uncovered branch or protocol state to a concrete input requirement. Examples include a missing netlink attribute producer, a device lifecycle transition, a packet layout, or a timer and teardown interleaving.

Record:

- The target file, function, branch, or state
- Current evidence that it is not reached
- The proposed campaign change
- The metric expected to move
- The observation window and acceptance criterion
- The rollback condition

“Increase coverage” is not a sufficient hypothesis.

## Isolate the experiment

Start from a corpus snapshot and a new work directory. Keep the kernel, image, VM resources, process count, and observation window fixed. Change one of:

- Seed programs
- Enabled syscall surface
- Syzkaller syscall descriptions
- Packet templates or mutation hints
- Focus weights
- Timing distribution
- Kernel instrumentation required to observe the state

When changing syscall descriptions, rebuild syzkaller and run its relevant generation and tests before starting guests.

## Measure target value

Prefer target-file line or program-counter coverage and meaningful state transitions over global coverage. Track whether new corpus entries exercise the target, not merely whether the overall corpus grows.

Reject an experiment when it only:

- Raises executions per second without reaching new target states
- Adds unrelated coverage
- Produces repeated infrastructure failures
- Requires a broad syscall surface that overwhelms the target signal
- Cannot be reproduced from recorded inputs and hashes

## Admit changes deliberately

If the experiment succeeds, preserve the new inputs, minimize them when appropriate, and document the measured delta. Merge them into the long campaign only after a smoke test with the final configuration. Keep the prior corpus snapshot so the change is reversible.

If it fails, retain the result as a decision record. Do not stack multiple speculative changes onto an inconclusive run.
