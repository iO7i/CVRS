"""Machine-readable finite v1 contract and support declaration."""
from cvsubstrate.foundation.identity import COMPONENT_VERSIONS
POLICY={
 'policy_version':'1.0','package_stage':'alpha','stable_python_facade':'cvsubstrate.v1',
 'component_versions':COMPONENT_VERSIONS,
 'lifecycle':{'stable':'Compatible readers/writers within this major; deliberate break requires new major or explicit migration.',
              'provisional':'Native integrations may need version-specific corrections; no certification inferred.',
              'internal':'No downstream compatibility promise.'},
 'stable_surfaces':['canonical identity','provenance graph','dependency closure','PromptSet','ScientificClaim','registry exchange 2.0'],
 'provisional_surfaces':['native driver internals','native trainer hooks','GPU export','experimental statistical diagnostics'],
 'tasks':['hbb','obb','masks','grounding'],
 'non_goals':['hosted service','cloud scheduler','all historical model conversions','video','pose','3D','live simulator control'],
 'legacy_readers':['worker protocol 1.0','registry format 1.0 preserved losslessly','existing prediction 1.0 contracts'],
 'canonical_json':'Python sorted compact JSON, finite numbers; not RFC8785/JCS',
 'no_percent_claim':'Requirement implementation and actual native/scientific execution are separate.'}
