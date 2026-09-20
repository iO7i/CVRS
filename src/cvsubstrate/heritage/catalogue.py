"""A metadata catalogue is not a model-support claim."""
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator, model_validator
from cvsubstrate.contracts.models import Contract, ID, SHA256, Finite, LicenseInfo, relative_path
from cvsubstrate.provenance.io import read_json, digest, write_json


class CatalogueEntry(Contract):
    id: ID
    family: str
    upstream: str = 'open-mmlab/mmdetection'
    source_url: str
    source_ref: str
    source_verified_on: str | None = None
    config_path: str | None = None
    paper_url: str | None = None
    checkpoint_url: str | None = None
    checkpoint_sha256: SHA256 | None = None
    reported_ap_percent: Finite | None = None
    dataset: str = 'COCO (exact split/protocol must be established for reproduction)'
    licenses: LicenseInfo = Field(default_factory=LicenseInfo)
    metadata_status: Literal['PRIMARY_METADATA_INSPECTED','DISCOVERY_ONLY'] = 'DISCOVERY_ONLY'
    execution_status: Literal['NOT_RUN'] = 'NOT_RUN'
    notes: str | None = None

    @model_validator(mode='after')
    def values(self):
        if self.config_path is not None:relative_path(self.config_path)
        if self.reported_ap_percent is not None and not 0 <= self.reported_ap_percent <=100:
            raise ValueError('AP metadata must be in percentage points, not mixed scales')
        return self


def load_catalogue(path: Path):
    payload=read_json(path)
    entries=[CatalogueEntry.model_validate(x) for x in payload['entries']]
    if len({e.id for e in entries})!=len(entries):raise ValueError('duplicate catalogue IDs')
    return entries


def compatibility_matrix(path: Path, *, local_source_root: Path | None=None):
    from cvsubstrate.provenance.io import safe_join, file_digest
    entries=load_catalogue(path);rows=[]
    for e in entries:
        local=None
        if local_source_root and e.config_path:
            p=safe_join(local_source_root,e.config_path)
            local={'exists':p.is_file(),'sha256':file_digest(p) if p.is_file() else None}
        rows.append({'id':e.id,'family':e.family,'metadata':e.metadata_status,
            'config':e.config_path,'local_config':local,'checkpoint_hash_known':e.checkpoint_sha256 is not None,
            'reported_ap_percent':e.reported_ap_percent,'inference':'NOT_RUN','metric_reproduction':'NOT_RUN',
            'compatibility_level':'H0_CATALOGUED','source_url':e.source_url})
    return {'schema_version':'1.0','catalogue_digest':digest([e.model_dump(mode='json') for e in entries]),
        'rows':rows,'limits':'Primary model-zoo metadata is not local checkpoint verification, installability, or reproduced performance.'}
