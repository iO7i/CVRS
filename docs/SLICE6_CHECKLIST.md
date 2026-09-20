# Slice 6 implementation map

All entries identify real files and entry points. Native/external execution, owner approval, and scientific verification are separate.

| ID | Requirement | Entry point |
|---|---|---|
| 6A.01 | Non-executing repository archaeology | `inspect-repo` |
| 6A.02 | Declared environment conflict explanations | `env explain` |
| 6A.03 | Reviewed no-rewrite paper wrapper | `wrap-repo; wrap-paper; paper validate/run` |
| 6A.04 | Source/input/checkpoint identity and change rejection | `paper validate/run` |
| 6A.05 | Detached multi-environment composition | `composition plan/run` |
| 6A.06 | Typed intermediate artifact ports | `composition plan/run` |
| 6A.07 | Source-attributed paper preparation packs | `recipe list/inspect/materialize` |
| 6A.08 | Paper/resource requirement inventory | `paper import; recipe assets` |
| 6A.09 | MMDetection/OneDL native packs | `stack list/run` |
| 6A.10 | MMRotate/MMYOLO/MMDeploy native packs | `stack run` |
| 6A.11 | MMSeg semantic-label integration | `stack run; bridge semantic-evaluate` |
| 6A.12 | Detectron2 native config/train/predict integration | `stack run` |
| 6A.13 | Modern specialist and promptable packs | `stack run` |
| 6A.14 | Environment capsules and image recipes | `env list/scaffold` |
| 6A.15 | Asset acknowledgement, fetch, verify and prune | `assets status/acknowledge/fetch/prune` |
| 6A.16 | Hugging Face and component identity | `hf inspect/local-lock; bridge run` |
| 6A.17 | Git source-state preservation | `source-git capture/materialize` |
| 6A.18 | Academic cluster handoffs | `env hpc` |
| 6A.19 | Methodology lint, review and experiment diff | `methodology lint; review; diff` |
| 6A.20 | Runnable reproduction exports and notebook API | `bridge reproduce; Python Experiment/Run` |
| 6B.01 | Supervision native HBB interchange | `bridge bundle-detections; bridge run` |
| 6B.02 | FiftyOne data/prediction bridge | `bridge run` |
| 6B.03 | W&B coexistence | `bridge tracking; bridge run` |
| 6B.04 | MLflow coexistence | `bridge run` |
| 6B.05 | DVC reference integration | `bridge run` |
| 6B.06 | HF and timm native bridges | `bridge run` |
| 6B.07 | TorchGeo dataset/sampler bridge | `bridge run` |
| 6B.08 | TerraTorch native job integration | `bridge run; stack run` |
| 6B.09 | OpenML compatible task/run metadata | `bridge run` |
| 6B.10 | Code Ocean export preparation | `bridge codeocean` |
| 6B.11 | Simulator-export provenance importers | `bridge simulator` |
| 6B.12 | Public benchmark exchange packs | `bridge benchmark` |
| 6B.13 | Isolated bridge security/lifecycle | `bridge list/run` |
| 6B.14 | Plain-file interoperability and loss reporting | `bridge commands` |
| 6C.01 | Canonical identity/version and owner approvals | `identity configure/derive` |
| 6C.02 | Public source sanitation | `release audit-public/public-tree` |
| 6C.03 | Public source/publishing separation | `release publish-bundle --preview` |
| 6C.04 | README and four documentation journeys | `docs build/serve/link-check` |
| 6C.05 | Generated API/CLI/schema references | `tools/dev.py reference` |
| 6C.06 | Observed environment doctor | `doctor` |
| 6C.07 | First-use project starters | `init; new project` |
| 6C.08 | Executable example gallery | `examples/public/*/run.py` |
| 6C.09 | Golden public demonstration | `demo-all` |
| 6C.10 | External adapter development experience | `adapter new/check; plugin commands` |
| 6C.11 | Public plugin metadata/compatibility discovery | `plugin list/inspect/validate` |
| 6C.12 | Actionable errors and safe support bundles | `support bundle; CLI errors` |
| 6C.13 | Packaging and optional environment recipes | `pip extras; env scaffold` |
| 6C.14 | Cross-platform developer commands | `check/lint/typecheck/docs/reference/public-preview` |
| 6C.15 | Public-safe CI and manual integration gates | `GitHub Actions configuration` |
| 6C.16 | Contribution and ownership workflow | `Repository templates` |
| 6C.17 | Governance/RFC/lifecycle contracts | `Documented review and deprecation rules` |
| 6C.18 | Independent version/compatibility surface | `release compatibility` |
| 6C.19 | Local release artifacts and manifest | `release publish-bundle; release build` |
| 6C.20 | License/attribution and dependency inventory | `licenses audit; release sbom` |
| 6C.21 | Trust-boundary documentation and safe inspections | `inspect-repo; review; support bundle` |
| 6C.22 | Static results, worker graph and image comparisons | `site results/graph/visual-diff` |
| 6C.23 | Static reproduction registry and exports | `research-registry export; site results` |
| 6C.24 | Citation/academic software metadata | `identity configure` |
| 6C.25 | Visual identity and design rationale | `Docs/static assets` |
| 6C.26 | Actual resource profiling | `profile` |
| 6C.27 | Historical compatibility fixtures | `release compatibility; existing migration commands` |
| 6C.28 | Read-only publication preparation and no lock-in | `public-tree; publish-bundle; bridge exports` |

## Limits are part of the contract

See `IMPLEMENTATION_LEDGER.json` for per-entry evidence and restrictions. No incompatible internal model graph is automatically split across workers. Native pack recipes are not validated environments, and no remote account/service was used to manufacture an adoption demonstration.
