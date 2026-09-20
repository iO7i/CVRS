# Use your models. Preserve the experiment.

For installation and execution boundaries, start with [the first-use guide](first-use.md). Version `0.7.1a3` is the prepared public-alpha candidate; it is not a stable 1.0 release.

After installation, `cvrs doctor` reports package presence without loading model implementations. Generate a project:

```bash
cvrs init my-project --profile detection
```

Install `.[native]` in a worker to execute its genuine random-initialized CPU model. Core installation only generates and validates data/contracts. It does not simulate model success.

## Frozen qualification browser

The source release includes an offline qualification browser at `qualification/h2/browser/index.html`, backed by the frozen H2 matrix and reviewed primary-evidence targets. Failed and blocked lanes remain visible by design.

## Choose a path

[Use an existing experiment](heritage.md), [design a research campaign](research.md), [extend through an adapter](extend.md), or [integrate existing tools](bridges.md).

The [pack reference](packs.md) and [command reference](commands.md) describe concrete inputs. [Security](security.md) explains execution and download boundaries. [Publication](publication.md) describes a clean, owner-reviewed release.

## Offline golden workflow

```bash
cvrs demo-all new-demo
```

After native dependencies are installed this uses no network and no pretrained assets. It creates real model runs, preserves raw/canonical predictions, re-evaluates them, and exchanges a research capsule. All research claims remain software-fixture scoped.

## Examples and references

[Eight public examples](examples.md) · [Generated API/CLI/schema references](reference/index.md)

## Product workflows

[Managed environments](managed-environments.md) · [Guided paper wrapping](guided-paper.md) · [Rich geometry exchange](rich-exchange.md) · [Methodology review](methodology.md) · [Research browser](browser.md) · [Owner-controlled release](release-process.md)

## Release status

[Public-alpha closeout and owner checklist](closeout.md). Native integration availability, observed local execution and scientific reproduction are separate claims.
