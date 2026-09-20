# Slice 6 handoff

Install the core/adoption package from this source tree:

```bash
python -m pip install -e '.[adoption]'
cvrs doctor
cvrs init my-experiment --profile detection
cvrs inspect-repo my-experiment
```

For the genuine CPU demonstration, install the optional native environment:

```bash
python -m pip install -e '.[native,adoption]'
cvrs demo-all my-demo
python tools/smoke_adoption.py my-paper-demo
```

The paper demo generates an independent PyTorch source repo and a separate standard-library converter. Neither imports CVRS. Source and input identities are recorded, and native detections are preserved. Its weights are random and the image procedural.

Review an existing repo without executing it:

```bash
cvrs inspect-repo ./paper-repo --out inspection.json
cvrs wrap-repo ./paper-repo --out paper-project --python /path/to/native-python
```

Review the generated `paper.json`, set exact commands and authorized inputs, then:

```bash
cvrs paper validate paper-project/paper.json
cvrs paper run paper-project/paper.json --operation predict --out new-result --trust
```

Build documentation and a clean owner-review source tree:

```bash
python tools/dev.py reference
cvrs docs build . --out ../cvrs-docs
cvrs docs link-check ../cvrs-docs
cvrs release public-tree . --out ../cvrs-public-preview --preview
cvrs release publish-bundle . --out ../cvrs-publication-preview --preview
```

Use new output directories. The preview is not an approved release: finalize `PUBLICATION.json` and the exact source-license grant first. Omitting `--preview` correctly blocks while those decisions remain unresolved. No publishing command contacts GitHub or PyPI.

Use `IMPLEMENTATION_LEDGER.json`, `docs/LIMITATIONS_06.md`, the public docs and `VERIFICATION_SUMMARY.json` for finite capability/evidence boundaries. Old reports are historical and retain their original meanings.
