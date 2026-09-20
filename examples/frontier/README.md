# Frontier examples

`tools/smoke_frontier.py` generates a fully executable CPU example with owned local random-initialized weights. It is the tested entry point; regenerate it on your machine.

The profile JSON files here are valid **configuration examples only**. They do not download models, supply weights, or certify preprocessing for an arbitrary upstream checkpoint. Use the profile matching the actual export graph and compare native outputs.

`grounding-job.template.json` deliberately uses a `.template.json` suffix: paths and SHA values must be replaced with the actual trusted local assets. It is not an executable pretrained-model demonstration. Generate its hashes using `cvsubstrate.provenance.io.file_digest` and record all required processor/tokenizer/config/weights files.

The registry is populated by `smoke_frontier.py`; all such claims carry `software_fixture`, not scientific results. It also produces a saved-prediction re-evaluation and static snapshot.
