# Public release and owner approval

The complete developer delivery and a clean public source tree are different artifacts. Historical test checkpoints, recovery ZIPs, local logs and session evidence do not belong in a default public source export.

```bash
cvrs release public-tree . --out ../source-preview --preview
cvrs release publish-bundle . --out ../publish-preview --preview
```

Preview mode is local and **not publishable as approved open source** while identity/license are pending. Credential findings block even a preview. The scanner is pattern-based; manual review remains necessary.

## Owner decisions

Edit a PublicationSettings JSON with actual authors, copyright holder, repository URL, security contact, chosen names and license. `identity configure` applies it to a working source tree only when explicitly invoked. Supply the exact approved license text. Package import renaming is a separate derived-source migration and must be reviewed as an API change.

```bash
cvrs identity configure . owner-settings.json --license-text approved-license.txt
cvrs release audit-public .
cvrs release publish-bundle . --out ../publish-final
```

No command pushes Git, publishes PyPI, deploys a site or uploads datasets. The builder writes source, wheel, sdist, docs, schemas, checksums, SBOM and a release manifest locally. The SBOM is a build-environment inventory, not a verified runtime supply-chain attestation.

## Compatibility

`release compatibility OLD NEW` statically compares public-looking API signatures, schemas and protocol inventories. It cannot prove behavioral compatibility. Prior artifact fixtures and genuine regression runs remain useful evidence.
