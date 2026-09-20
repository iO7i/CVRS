# Owner-controlled release process

This alpha contains release tooling. It is not a published package, an approved
license grant or a public repository. Complete and approve `PUBLICATION.json`
with the final authors/copyright, repository URL, security contact, package/CLI
identity and exact source license before attempting publication.

```bash
cvrs release preflight .
cvrs release launch-plan . --out launch-plan.json
cvrs release freeze-api . --out api-surface.json
cvrs release contribution-check .
```

## Build, attest, publish: separate privilege boundaries

The checked-in release workflow is manual and disabled until the repository
variable `CVRS_PUBLISH_ENABLED` is explicitly true. The requested tag must exactly
match the package version. The build job checks approved identity, clean source,
tests and public-tree sanitation, then produces wheel/sdist/SBOM/manifests with no
publishing credentials or OIDC permission.

Separate jobs download only the built artifacts. Attestation uses GitHub's
artifact/SBOM attestation action. PyPI/TestPyPI publishing uses OIDC Trusted
Publishing in a protected environment, with no source checkout or repository
script execution in that publishing job. PyPI's trusted-publisher mapping and
GitHub's protected environments must be configured by the owner. A workflow file
cannot create those external trust decisions.

`tools/release_ci.py` emits an artifact manifest and verifies wheel/sdist metadata
and hashes. Actions are pinned to the immutable commits in `action-lock.json`.
A pin is not proof the workflow ran; no hosted Actions run occurred in this build.

## Repository security: plan first

```bash
cvrs release security-plan OWNER/REPO --files 'Core (3.13)' --out security-plan.json
```

Review the plan before invoking `security-apply` with `--apply` and its exact
digest. That command is an actual remote write and requires an authorized token
in the environment. Existing branch protection cannot be replaced without its
reviewed state hash. After each operation the requested fields are read back.
Failures stop the sequence and retain which earlier changes already applied.

The plan covers secret scanning/push protection, vulnerability alerts, automated
security fixes, private reporting and explicit branch checks. It does not assume
features are available under every account policy, buy paid features, or conceal
permission failures. No remote security operations were performed here.

## Documentation and academic archiving

`docs portal` generates a searchable offline site. `docs version-site` combines
already-generated versions without rewriting old pages. GitHub Pages deployment
requires `CVRS_PAGES_ENABLED` and an approved Pages environment.

`release citation-pack` emits owner-approved CFF/CodeMeta and archive instructions.
A DOI appears only with an explicit matching owner-supplied archive receipt. It is
never generated from a guess. Enable Zenodo's GitHub release archiving yourself,
then record the real returned DOI. This tooling does not claim it contacted or
verified Zenodo.

## Public source versus engineering evidence

Use the sanitized public preview for owner review, not the full developer archive
with historical runs. Public preview may tolerate pending owner decisions, but
not detected credentials. Final publication uses the non-preview path. Pattern
scanning cannot prove no secret of an unknown format exists; review remains
necessary.

## This alpha candidate

Follow the [finite publication-closeout checklist](closeout.md). Use the clean tree generated from the hardened candidate, not an older preview. Keep the exact artifact hashes with your own test outcomes. Retained historical reports do not become current passes.
