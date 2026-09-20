"""No automatic leaderboard when the measurement protocols differ."""
from cvsubstrate.provenance.io import digest

def compare(left: dict, right: dict) -> dict:
    a = left.get('comparison_key')
    b = right.get('comparison_key')
    required = {'dataset_digest', 'split', 'sample_ids', 'taxonomy', 'evaluation_protocol'}
    if not isinstance(a, dict) or not isinstance(b, dict) or (not required.issubset(a)) or (not required.issubset(b)):
        return {'status': 'DESCRIPTIVE_ONLY', 'differences': ['one or both results lack a complete comparison key'], 'training_fairness': 'NOT_ASSESSED'}
    differences = [key for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key)]
    declared_digests_ok = left.get('comparison_digest') == digest(a) and right.get('comparison_digest') == digest(b)
    if not declared_digests_ok:
        differences.append('comparison_key_integrity')
    return {'status': 'INCOMPARABLE' if differences else 'COMPARABLE_UNDER_DECLARED_PROTOCOL', 'differences': differences, 'training_fairness': 'NOT_ASSESSED', 'note': 'Comparable measurement does not prove fair training budgets, meaningful uncertainty, or model superiority.'}
