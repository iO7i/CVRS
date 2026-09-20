# CVRS 0.7.1a1 — narrow compatibility and provenance hardening

19 September 2026. Patch to 0.7.0a1; no package reorganization, feature expansion, or blanket cleanup.

The original release ZIP is unchanged: `e90bcb7ca6db2b0f487a548a09c3d3d295068817d93dbab6323a5312553f30a9`. Historical reports, coverage, source documentation and native-worker implementations are retained.

## 1. Explicit public exports, with the snapshot reader aligned

`cvsubstrate.v1.__all__` now explicitly lists the same **59 names**, in their prior order. A helper import can no longer accidentally expand wildcard exports.

`product.compatibility.freeze_api()` reads literal list/tuple export declarations without importing the inspected source. It honors an empty list and explicit aliases. Duplicate, invalid, missing or unresolved/mutated export boundaries fail with a descriptive error instead of producing a misleading partial snapshot. The former implicit-import rule and exact historical dynamic `__all__` comprehension remain supported for historical facades. This is a finite static facade reader, not a Python interpreter.

Before/after public API snapshots are **identical**, including all **129 schema definitions** and component versions. Their surface digest is `cef3a07a8b11e96e29714cc50c3c23e617ec2a558ba271e7cbd53c18ab19794c`. No command, public symbol, model operation, schema or protocol was added or removed.

## 2. Additive package-payload identity

`source_snapshot()` still provides `package_files`, `package_tree_digest`, and `git` with their historical meaning. In particular, `package_tree_digest` remains the canonical digest of the Python-only file-hash map. The numerical value naturally changes when Python source/version bytes change; its algorithm and interpretation do not.

A new **optional `package_payload`** field records a separately versioned fingerprint. Its selected scope is:

- Python files and type stubs under the package, plus the root `py.typed` marker.
- Regular packaged files under `resources/`, including recipes, templates and UI/configuration resources.
- Package-relative paths and file SHA-256 values; selection policy and partial-observation status are bound into the root digest.

Bytecode, declared cache directories and version-control directories are excluded. The new payload scan does not follow links; the legacy Python-only scan retains its historical hashing behavior. Selected file links, directory links and unreadable selected paths are reported as **PARTIAL**, never silently certified as complete. There is no recursive traversal of user datasets, model caches or external directories.

Resource edits, additions, removals and renames alter this new identity even when all Python bytes remain identical. File timestamps and installation paths do not. **The 277 selected files match across this source tree, the wheel bytes and an installed wheel copy.**

This is a fingerprint of selected package bytes at observation time—not a dependency closure, wheel archive hash, execution trace, filesystem-atomic snapshot, signature or proof of computation. Repository-level generated schemas/docs, dependencies, datasets, native environments and external assets are separate identities.

Old run records do not need the new field. Their readers and verification rules are unchanged. Existing callers that already emit `source.json` gain the extra field automatically; other evidence formats were not rewritten.

## 3. Preserve historical inventories during release preparation

Packaging checks exposed one additional narrow preservation defect: `prepare_release()` excluded `RELEASE_MANIFEST.json`, `SBOM.cdx.json`, and `LINE_COUNTS.json` by basename at any depth. That also omitted nested historical copies. A regression reproduced the failure before the fix.

The exclusion now applies only to the **current top-level** inventories that will be regenerated. Historical nested files are copied unchanged. The two affected files from the input archive were restored byte-for-byte, and a regression covers all three historical inventory names. No historical record was rewritten or relabeled. This is a one-condition release-copy fix, not a packaging reorganization.

## 4. Verification performed in this patch

| Check | Observed result |
|---|---|
| Focused regression tests | **33 passed**; included in the full-suite total |
| Full regression suite | **682 passed, 5 skipped, 0 failures, 0 errors** |
| Public facade | Same 59 names and identical full API/schema snapshot |
| Legacy source fields | Same Python-only algorithm, tested independently against file bytes |
| Package resources | Resource/type changes affect only the additive identity when Python is unchanged |
| Filesystem behavior | Location/mtime invariance, declared cache exclusion, link non-following, unreadable-file partial status |
| Historical runs | Legacy-only and additive source records both seal and verify; changing a sealed record is detected |
| Wheel isolation | Installed-wheel facade/snapshots work under `python -S` with only copied Pydantic runtime modules; no ML/geospatial libraries available |
| Real CPU smoke | Installed-wheel controller launches a genuine torchvision detector in a separate interpreter; four prediction-image records, 18 verified artifacts, new payload recorded in `source.json` |

The five skipped tests need unavailable `pycocotools`. No metric fallback, package download, paid compute or remote publication occurred. The CPU smoke uses random weights and procedural fixtures, not pretrained or scientific evidence. The 33 focused tests are **not** an additional 33 on top of the full-suite count.

## 5. Current coverage: explicitly scoped, not a completion score

The new report covers **260 current product Python modules** and collects branches. It instruments **the pytest process only**. Child worker interpreters are not instrumented, even when their real execution passes; code directly called inside pytest is measured. Optional integrations unavailable to the test environment remain unevaluated.

- Statements measured: **10,613/17,294 (61.37%)**.
- Branches measured: **3,412/7,910 (43.14%)**.
- Coverage.py combined statement/branch figure: **55.65%**.

No arbitrary threshold was added. This is a baseline for this measurement scope, not a native-stack coverage claim or an estimate of software/scientific completeness. **It is not comparable to the historical approximately 71% report**, which covered 29 modules without branch measurement. `evidence/coverage.json` remains byte-for-byte unchanged.

The current raw results, per-file and per-function coverage, exact commands, tool versions, source snapshot, wheel checks and smoke outputs are under `evidence/hardening-0.7.1/`. No old evidence is relabeled as a current pass. Ruff and mypy were not run.

## 6. Deliberately unchanged

Package layout; `adoption`/`product` responsibilities; all CLI command paths; standalone native worker files and interpreter constraints; model preprocessing, taxonomy, metrics and training semantics; experiment identity; dataset mappings; registry evidence rules; compatibility policy; owner identity/license/publication gates; historical documentation.

No sandbox, new signing path, directory-ingestion feature, dependency update, refactoring campaign, coverage threshold or support-matrix expansion was introduced.

## 7. Review and rerun

- `cvrs-0.7.1-hardening.patch` accompanies the download and contains the exact product/version/test changes and their small documentation/packaging updates.
- `tests/test_hardening_071.py` exercises the targeted changes and historical compatibility.
- `evidence/hardening-0.7.1/verification-summary.json` separates the checks and their limits.
- The bundled wheel is built from the patched package; the release manifest identifies all delivered bytes.

For focused local checks after installation:

```bash
python -m pytest -q tests/test_hardening_071.py
```

For a fresh coverage baseline with the same scope, use a new output directory and coverage data file:

```bash
python -m coverage run --branch --source=src/cvsubstrate -m pytest -q
python -m coverage json -o coverage-pytest-process.json
```

Disable third-party pytest plugin autoload and limit native BLAS/OpenMP threads when reproducing the recorded environment; the executed command/environment are documented in `current-suite-status.json`. Do not overwrite the bundled historical evidence.
