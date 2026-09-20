# Public-alpha release closeout

CVRS `0.7.1a3` is the prepared public-alpha candidate. This closeout changes publication metadata, packaging completeness and qualification-browser accessibility; it does not add another model, task, scientific campaign or compatibility claim.

## Approved public identity

| Field | Value |
|---|---|
| Project | CVRS / CV Research Substrate |
| Author | Hosam Talbi (`iO7i`) |
| Copyright | Hosam Talbi |
| Distribution | `cv-research-substrate` |
| Import | `cvsubstrate` |
| CLI | `cvrs` |
| Repository | `https://github.com/iO7i/CVRS` |
| Source license | Apache-2.0 |
| Security route | `https://github.com/iO7i/CVRS/security/advisories/new` |

The security route must be enabled through GitHub private vulnerability reporting before the public announcement. No DOI is claimed until an archive actually exists.
## Release procedure

Run the release gates on the exact candidate:

```bash
cvrs release preflight . --out ../release-preflight.json
cvrs release public-tree . --out ../cvrs-public-source
cvrs release publish-bundle . --out ../cvrs-publication
```

Do not use `--preview` for the publishable candidate. Review the generated public tree, qualification-browser evidence links, license/notice files, and all recorded hashes before any remote push.

## Artifact completeness gates

The final source distribution must retain the files required by its own distributed tests, including `docs/reference-cases` inputs and `tests/compat` fixtures. The public source must retain the frozen H2 qualification browser, its matrix, and only the reviewed primary-evidence files referenced by that matrix.

The hash-bound RQ001 document and historical compatibility fixtures use LF bytes. `.gitattributes` pins those paths to LF so a Windows checkout cannot silently invalidate their recorded digests.

## Claim boundaries

A package install is not native-model certification. A hash match is not scientific validation. A passing qualification lane is scoped to its declared route. Failed fidelity cases, native-runtime failures, and external-access blockers remain first-class outcomes rather than being rewritten as support.
## Final owner checklist

1. Confirm non-preview preflight is `PASS`.
2. Confirm the complete local regression suite, maintained-scope typecheck, Ruff, strict documentation build, public export audit and package roundtrip are green on the exact final tree.
3. Open `qualification/h2/browser/index.html` from the exported public source and verify every declared public evidence target resolves.
4. Install the final wheel in a clean environment and execute the documented first-use controller path.
5. Enable GitHub private vulnerability reporting.
6. Show and review the final README.
7. Only then create/push the repository, tag `0.7.1a3`, and mark the GitHub release as a prerelease/public alpha.

No remote publication is performed by these local preparation steps.
