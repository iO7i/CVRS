# Local research browser

```bash
cvrs site build ./research-results --out ../research-browser --verify
```

The browser is static HTML, CSS, JavaScript and an equivalent JSON catalogue. It
uses no API, login, CDN or telemetry. It exposes experiments, model identities,
datasets, claims, reproduction attempts, record details and comparisons.

Search and filters operate on local data. Comparison checks task, dataset and
evaluation identities. Missing or mismatched identities disable numeric deltas;
matching identities still do not prove controlled training conditions. Details
show underlying evidence rather than replacing it with one ambiguous green tick.

No source run is mutated, no model checkpoint or dataset image is copied, and
metadata export failures are visible. Registry reads are read-only. Sensitive
metadata still needs owner review before hosting the static files publicly.

Browser loading, search, navigation, responsive layout and dialogs are separate
software checks from ML correctness. A screenshot is not proof of a benchmark.
