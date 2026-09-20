# Research protocol semantics

The four executable micro-campaign arms are R, S, R+S, and S→R. The fixture tags are
mock real/synthetic accounting labels; all included images are procedural software
fixtures. No transfer improvement is asserted.

## What is held constant

R and R+S use the same real sample sequence for a given seed and real exposure
budget. R+S adds a separately seeded synthetic sequence. One optimizer update is
performed per step. Native detector losses are computed separately by source and
combined as `real_loss + synthetic_weight * synthetic_loss` before backward/update.
There is no claim that this equals concatenating the sources into one batch.

`synthetic_weight` is a nominal loss weight. It is not a measured share of gradient
influence. Source-forward Torch RNG is explicitly seeded per step, so synthetic
proposal sampling does not consume the real source RNG. Different learned weights
can still alter proposals. There are no stochastic image augmentations to equate.

Matching real exposure does not match compute, total examples, or wall time.
Matching optimizer steps likewise does not match source exposure. The plan records
these differences instead of claiming a universally fair comparison.

## Stages

S→R performs synthetic pretraining, keeps model weights, then resets optimizer and
scheduler before real fine-tuning. It has more total updates than R. Scientific use
should add an appropriate real-pretraining/replay or compute-matched control before
attributing differences specifically to synthetic information.

Plans contain planned exposures, unique samples, replay counts, and optimizer
updates. Measured values live in worker execution and training traces. The runner
checks actual counts against the plan. Unknown-source samples are excluded, never
silently classified as real. A required empty source pool fails.

## Split protection

Training requires a train-role split. Development evaluation requires dev. A
locked-test run must be a separate inference-only experiment and carry a record
bound to its experiment digest, dataset digest, and split. A training run cannot
access locked test even when someone supplies an authorization record.

Exact sample overlap, identical image hashes, declared lineage groups, and
transitively connected parent IDs cannot cross split boundaries. These checks do
not detect undeclared common flight paths, near-duplicates, content-based contamination,
or a malicious actor editing the policy. They are local research guardrails, not
cryptographic secrecy or a sandbox.

## Domain-specific diagnostics

The diagnostic evaluator reports support and fixed-threshold detection counts by
explicit domain tag, and matched-ground-truth recall by bounding-box pixel area.
Unknown domains remain unknown. A mixed-domain aggregate is not a desert-domain
score. Tiny slices are descriptive; no confidence interval or significance claim
is generated. Independent final datasets, multiple fresh seeds, appropriate group
resampling, and sealed-test governance belong in the next scientific release.
