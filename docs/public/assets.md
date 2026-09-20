# Model and dataset identity

```bash
cvrs hf inspect organization/model --revision COMMIT --allow-network
cvrs hf local-lock local-model --repo-id organization/model --revision COMMIT --out model-lock.json
```

Metadata inspection does not download model files. A model identity includes processor/tokenizer/configuration files, not just the large weight tensor. Git blob IDs are not SHA-256 file hashes.

## Explicit transfers

The asset manager requires a descriptor with source, expected SHA-256, license metadata and optional size. A user acknowledges that exact descriptor and purpose before fetching. Acknowledgement is not a legal grant.

```bash
cvrs assets acknowledge asset.json --cache ./assets --actor local-user --purpose research
cvrs assets fetch asset.json --cache ./assets --max-bytes 1000000000
cvrs assets status asset.json --cache ./assets
cvrs assets prune --cache ./assets --keep DIGEST
```

Local file transfer is offline. HTTPS requires `--allow-network`. Resuming verifies the complete final digest; mismatches are quarantined. No automatic archive extraction or model execution occurs. Pruning is dry-run unless `--apply`; retain all referenced digests.

HF selected-file downloads additionally need an explicit allowlist, transfer acknowledgment and byte budget. Floating revisions become resolved commits in the receipt; unknown sizes or implicit bulk requests fail.
