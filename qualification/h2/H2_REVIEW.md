# H2 Alpha Freeze — final review

Status: `H2_ALPHA_CANDIDATE_READY`

CV Research Substrate `0.7.1a3` is a hardened local alpha candidate, not a
public release and not a 1.0 claim. RQ001 and RQ002 remain separate reference
qualifications, and each lane reports implementation, native execution,
artifact fidelity, evaluator/deployment fidelity, and portability separately.

## Frozen foundation-model outcomes

- DINOv2 ViT-S/14: `PASS`.
- SAM 2.1 Hiera Tiny: `FAIL_NATIVE_RUNTIME_COMPATIBILITY`; native Transformers
  mask postprocessing failed after GPU forward and before CVRS conversion.
- SAM 3: `BLOCKED_EXTERNAL_ACCESS`.
- DINOv3: `BLOCKED_EXTERNAL_ACCESS`.
- Grounding DINO: the corrected retry already passed and was not rerun.
- No additional substitute model was introduced.

## Release and clean-room evidence

- 568 tests pass; 105 optional/native/platform tests skip with reasons in the final local release run. The earlier disk-full attempt is not counted as a product failure.
- Ruff passes. Mypy passes the documented 35-file maintained surface.
- MkDocs strict build passes; 785 local links resolve.
- The wheel installs directly. The sdist independently rebuilds to an
  installable wheel. Different wheel hashes are recorded without claiming
  binary reproducibility.
- A wheel-only clean room imported CVRS from `site-packages` with no source
  checkout and no ML frameworks. It verified 16 RQ001 manifest entries, 15
  RQ002 evidence references, a 33-file portable capsule, and the 20-lane H2
  browser. It recomputed DINOv2 nearest-neighbor retrieval from saved evidence
  without rerunning the model. Tamper and missing-file controls were rejected.
- The post-upgrade dependency audit reports zero known vulnerabilities. The
  initial finding was isolated to old venv-bootstrap pip and is retained.
- Native Windows symlink fixtures could not be created under current
  privileges, so those checks are classified
  `SKIPPED_PLATFORM_PRIVILEGE_NOT_DEFECT`; portable archive symlink rejection
  remains covered by passing tests.

## Honest release boundary

Owner publication metadata is now configured for Hosam Talbi (`iO7i`),
Apache-2.0, and `https://github.com/iO7i/CVRS`. The remaining requirement is
mechanical release verification on the exact corrected tree. No remote publication,
upload, tag, or release has occurred.
