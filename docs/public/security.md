# Trust and data boundaries

Legacy Python configurations, plugins, native entrypoints and some checkpoint formats can execute code. Process separation protects dependency compatibility, not the machine from hostile code.

Repository inspection uses static parsing. It does not import setup.py or evaluate dynamic configs. Candidate commands never auto-execute. All native wrapper operations require explicit reviewed trust. Do not execute untrusted checkpoints/configurations on a privileged CI runner.

## Network

Core workflows are local. Optional SDK bridges require explicit permission before remote transfer. Worker offline flags/socket guards are defense-in-depth, not a substitute for OS isolation; native subprocesses/extensions may need container/network controls for hostile inputs.

## Public artifacts

Support bundles use an allowlist and redaction; inspect the resulting archive before sharing. They exclude model weights and source data by default. Visual diffs require explicit image-copy approval. Git source capsules can include historical secrets even if the current worktree is clean.

## CI

Pull-request workflows have read-only permissions, no persisted checkout credentials and no self-hosted GPU runner. Trusted native/asset jobs require manual invocation and an environment approval configured by the owner. Labels alone do not authorize executable external assets.

## Disclosure

The private security-reporting contact remains an owner decision. Do not invent an email address or post sensitive exploit details publicly while that route is unresolved.
