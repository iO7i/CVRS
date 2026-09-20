# Primary source references — inspected 19 September 2026

Used to implement finite API and workflow paths, not to assert native execution.

- uv environments: https://docs.astral.sh/uv/pip/environments/
- uv CLI: https://docs.astral.sh/uv/reference/cli/
- conda create: https://docs.conda.io/projects/conda/en/stable/commands/create.html
- Docker build: https://docs.docker.com/reference/cli/docker/buildx/build/
- Apptainer builds: https://apptainer.org/docs/user/latest/build_a_container.html
- Supervision detections: https://supervision.roboflow.com/0.30.1/detection/core/
- FiftyOne labels: https://docs.voxel51.com/user_guide/using_datasets.html
- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- GitHub attestations: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- GitHub repository REST: https://docs.github.com/en/rest/repos/repos
- GitHub branch protection: https://docs.github.com/en/rest/branches/branch-protection
- Zenodo CITATION.cff: https://help.zenodo.org/docs/github/describe-software/citation-file/
- Zenodo repository activation: https://help.zenodo.org/docs/github/enable-repository/

Immutable action commits and inspected release tags are in
`src/cvsubstrate/resources/product/action-lock.json`. No floating tag is used in
privileged workflows. Source URLs and dates for the ten preparation recipes are
in each recipe's metadata; they remain unexecuted preparation entries.
