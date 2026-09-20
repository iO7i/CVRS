# Stop-or-redirect assessment

The implemented proof has concrete value: the controller does not import Torch;
a separate interpreter really trains a detector; predictions are checked against
sample and geometry contracts; data/protocol mismatches are detectable; measured
source exposure is retained; and runs can be checked after moving the archive.

That is sufficient to continue a **small experiment/evidence package**, not enough
to justify a universal vision framework. Only one native detector has been executed.
The official evaluator and heritage worker remain unverified in this environment.
No external researcher has demonstrated that this improves their work.

The next evidence test should use one existing MMDetection model and one modern
native detector on an appropriate redistributable or user-provided dataset, with
the same explicitly pinned reference evaluator. Measure adapter effort, semantic
exceptions, reproduction fidelity, and whether someone can use it without editing
core code. Get an independent user to repeat the workflow.

Redirect to a narrower evaluation/provenance tool if model interfaces keep requiring
core changes, if native behavior cannot be preserved, or if existing tools plus a
short script already deliver the same auditable workflow. Contribute fixes upstream
or to a maintained fork rather than creating a second CUDA maintenance universe.

Do not describe this foundation as world-class based on test counts or generated
documentation. Its claim is that future research and compatibility claims now have
concrete places to put evidence and explicit ways to fail.
