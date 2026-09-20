# 0.7.1a3 — public-alpha release candidate

**Status: release-prepared locally; not remotely published; not stable v1.**

This candidate freezes CVRS Reference Qualifications 001 and 002, ships the offline qualification browser with reviewed public evidence targets, and keeps successful, failed and externally blocked outcomes distinct. It adds no model, dataset, scientific campaign or qualification scope.

## Release corrections

- Restored the canonical LF bytes for the hash-bound RQ001 reference document and historical compatibility fixtures, and pinned those paths with `.gitattributes`.
- Completed public identity metadata for Hosam Talbi (`iO7i`), repository `iO7i/CVRS`, Apache-2.0 licensing, and GitHub private security reporting.
- Made the frozen qualification browser and its reviewed primary-evidence targets part of the public source/export contract.
- Included the reference-case inputs and historical compatibility fixtures required by tests shipped in the source distribution.
- Hardened browser history restoration, filter/selection consistency, mobile focus management, table semantics, evidence navigation and low-contrast technical text.
- Retained all red qualification outcomes and external-access blockers without reclassifying them.
## Claim boundary

CVRS remains an alpha interoperability/evidence system. A successful package install does not certify optional native frameworks, GPUs, datasets or official benchmark reproduction. The qualification matrix reports only the routes actually evidenced.

See `PUBLIC_STATUS.json`, `qualification/h2/H2_REVIEW.md`, and `docs/public/closeout.md` for the exact release boundary.
