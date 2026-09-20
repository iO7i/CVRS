# Geometry-preserving exchange

Rich interchange records distinguish HBB, quadrilateral OBB, instance masks and
grounded phrases. They retain dataset identity, category mapping, original image
coordinates, instance IDs, prompts, licenses and provenance. Every round trip can
be audited against the original values.

```bash
cvrs exchange export canonical.json --format fiftyone --out native-view.json
cvrs exchange import native-view.json --format fiftyone --out restored.json
cvrs exchange audit canonical.json restored.json
```

Supervision transport uses xyxy, confidence, class_id, optional binary masks,
optional quadrilateral coordinates and explicit identity metadata. FiftyOne OBBs
use closed polygon corners. Instance masks use pixel-aligned cropped windows;
the independently predicted detector box is retained separately. Edited native
geometry is read on import rather than silently restored from cached originals.
Fractional mask windows that would need resampling are rejected.

`exchange native` uses actual installed SDKs in a separately selected interpreter
and emits the native view, restored canonical records and an audit. The software
payload round trip and native SDK execution have separate evidence statuses.
Official benchmark metrics are not inferred from a converter test.

TerraTorch or another native array producer can use `exchange decode` with a
reviewed schema to map finite NPZ HBB arrays or semantic label/logit maps. It
requires actual dimensions, labels, ignore-index and score semantics. It never
loads pickle or guesses a task from arbitrary tensors. Semantic outputs remain
label-map artifacts, not instance masks.

W&B/MLflow handoffs contain verified run identity and explicitly approved
artifacts; remote SDK calls remain opt-in. DVC, HF, TorchGeo and existing native
bridges retain their scoped contracts. No service account is contacted by
preparing a payload.
