# Write a small adapter, not another model implementation

```bash
cvrs adapter new my_model --out my-adapter
```

The minimal scaffold advertises validation only until the author implements real operations. For an executable native-delegating example use `--native-vision`. Never advertise predict/train merely because a method name exists.

The descriptor records kind, target, protocol, operations and tasks. Install the adapter in its own environment. Registration requires explicit trust. Use `plugin conformance` to check the implementation; `adapter check` checks only its manifest.

## Bring arbitrary paper code

The generic paper wrapper often needs less code than a framework adapter: exact argv, local inputs, required outputs and a conversion to an existing canonical task. Keep native checkpoint generation and model behavior native.

## Inter-worker artifacts

Images, embeddings, feature maps, detections, masks, prompts and checkpoints carry content hashes and producer identities. Tensor artifacts declare shape, dtype, sample IDs, layer/stride/channel semantics where needed. A consumer's port requirement must match.

```bash
cvrs composition plan composition.json
cvrs composition run composition.json --out new-composition --trust
```

This is detached file transfer. `requires_grad` and cross-worker training requests fail explicitly. Nothing automatically ports a model graph.

## Public Python interface

```python
from cvsubstrate.adoption.api import Experiment
result = Experiment("experiments/baseline.json").run("new-run")
print(result.verify())
print(result.metrics())
```

The CLI calls the same services. Downstream code should not import standalone worker internals.
