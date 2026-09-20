# Trust and threat model

Trusted: owner-supplied Python executables, installed packages, native worker code,
explicitly trusted legacy configs/checkpoints, and the local operating system.
Untrusted/mistake-prone: JSON records, declared outputs, file paths, annotation
geometry, dataset membership, recorded hashes, process exit status, and log content.

Controls include strict schemas, finite numbers, duplicate-key rejection, bounded
JSON, safe relative paths, symlink escape checks, sample-universe validation,
content hashes, redundant controller/worker policy validation, no shell interpolation,
restricted inherited environment, bounded output capture, deadlines, and lifecycle
records for success/failure/cancellation. No model/dataset acquisition is automatic.

These controls do **not** make Python configs or pickles safe. A subprocess and a
virtual environment are not a sandbox. A trusted worker can still read accessible
files, write files permitted by the OS, or evade basic network guards. Use actual
container/OS restrictions before executing unknown research code.

Logs receive best-effort redaction of common credential assignments and URL
credentials. That is not proof that all sensitive values are removed. Review
artifacts before publication. Run manifests avoid copying datasets, home directories,
and arbitrary checkpoints into the repository by default.

Unsigned hashes detect ordinary alteration relative to the supplied manifest, but
an attacker controlling both artifacts and manifest can replace both. Dataset
hashes are checked before and after normal runs; this is not protection against a
hostile perfectly timed TOCTOU attack. File headers are checked for dimensions;
image decoding belongs to Pillow/the worker and malformed image hardening remains
an upstream responsibility. Do not feed untrusted decompression bombs unrestricted.

Locked-test policy is not cryptographic test secrecy. The owner can edit files and
roles. External adoption, independent review, supply-chain signing, malicious-worker
sandboxing, race-safe storage, and stronger distributed provenance are future work.
