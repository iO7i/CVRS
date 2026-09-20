"""Namespaced identities and a generic acyclic provenance graph.

This uses CVRS Python canonical JSON v1, not JCS/RFC8785. Semantic IDs exclude
locations only when the caller explicitly declares them nonsemantic. No guessed
normalization of float values, categories, lists, or model preprocessing.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field, model_validator
from cvsubstrate.contracts.models import Contract, SHA256, ID
from cvsubstrate.provenance.io import digest

COMPONENT_VERSIONS = {
    'canonical_json': 'cvrs-python-json/1', 'public_api': '1.0',
    'worker_legacy': '1.0', 'worker_session': '2.0', 'plugin': '1.0',
    'capsule': '1.0', 'registry_legacy': '1.0', 'registry_exchange': '2.0',
    'provenance_graph': '1.0',
}
IDENTITY_KINDS = frozenset({'dataset','sample','model','checkpoint','experiment',
    'run','prediction_set','evaluation','claim','attempt','benchmark','environment',
    'asset','prompt_set','ontology','edge','artifact','protocol','actor','record'})

def content_id(kind: str, value: Any) -> str:
    if kind not in IDENTITY_KINDS:
        raise ValueError('unknown identity kind: '+kind)
    return kind+':'+digest({'kind':kind,'identity_version':'1.0','value':value})

class ProvenanceNode(Contract):
    id: ID
    kind: str
    content_sha256: SHA256
    metadata: dict[str, Any] = Field(default_factory=dict)

class ProvenanceEdge(Contract):
    source: ID
    target: ID
    relation: Literal['derived_from','produced','consumed','evaluated_by',
        'supported_by','contradicted_by','reproduced_by','superseded_by','uses',
        'contains','trained_on','initialized_from','generated_from']
    evidence: list[SHA256] = Field(default_factory=list)
    @model_validator(mode='after')
    def distinct(self):
        if self.source==self.target: raise ValueError('self lineage edge')
        return self
    @property
    def identity(self):return content_id('edge',self)

class ProvenanceGraph(Contract):
    nodes: list[ProvenanceNode]
    edges: list[ProvenanceEdge]
    @model_validator(mode='after')
    def valid(self):
        ids=[x.id for x in self.nodes]
        if len(ids)!=len(set(ids)):raise ValueError('duplicate graph node')
        if len({e.identity for e in self.edges})!=len(self.edges):raise ValueError('duplicate edge')
        if any(e.source not in ids or e.target not in ids for e in self.edges):raise ValueError('dangling edge')
        # All graph edges are directed. Authors must not publish mutually inverse
        # representations of a relationship in the same DAG.
        children={i:[] for i in ids}
        for e in self.edges:children[e.source].append(e.target)
        state={}
        def visit(n):
            if state.get(n)==1:raise ValueError('provenance cycle')
            if state.get(n)==2:return
            state[n]=1
            for c in children[n]:visit(c)
            state[n]=2
        for n in ids:visit(n)
        return self
    def ancestors(self, node_id: str) -> list[str]:
        if node_id not in {n.id for n in self.nodes}:raise KeyError(node_id)
        # Follow declared outgoing derivation/uses edges; direction is preserved.
        seen=set();todo=[node_id]
        while todo:
            n=todo.pop()
            for e in self.edges:
                if e.source==n and e.target not in seen:seen.add(e.target);todo.append(e.target)
        return sorted(seen)
    @property
    def identity(self):
        return digest({'nodes':sorted([n.model_dump(mode='json') for n in self.nodes],key=lambda n:n['id']),
                       'edges':sorted([e.model_dump(mode='json') for e in self.edges],key=digest)})

SCHEMAS=[ProvenanceNode,ProvenanceEdge,ProvenanceGraph]
