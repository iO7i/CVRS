import json

import pytest

from cvsubstrate.product.qualification_browser import render_qualification_browser


def matrix():
    lane = {"reference":"CVRS_REFERENCE_001","lane":"demo","disposition":"PASS","implementation":"PASS","native_execution":"OUT_OF_SCOPE","artifact_fidelity":"PASS","evaluator_or_deployment":"OUT_OF_SCOPE","portable_evidence":"PASS","evidence":"evidence.json"}
    references = [
        {"id": "CVRS_REFERENCE_001", "title": "Legacy", "summary": "Legacy workflow"},
        {"id": "CVRS_REFERENCE_002", "title": "Modern", "summary": "Modern workflow"},
    ]
    return {"schema":"cvrs.h2.qualification-matrix.v1","candidate_version":"0.7.1a3","references":references,"lanes":[lane]}


def test_h2_browser_is_offline_and_separates_dimensions(tmp_path):
    source = tmp_path / "matrix.json"
    source.write_text(json.dumps(matrix()), "utf-8")
    result = render_qualification_browser(source, tmp_path / "site")
    text = (tmp_path / "site" / "index.html").read_text("utf-8")
    assert result["external_network_required"] is False
    assert "Native Execution" in text and "Artifact Fidelity" in text
    assert "http://" not in text and "https://" not in text
    assert "Research Observatory" in text
    assert 'id="global-search"' in text
    assert 'id="inspector"' in text

    script = (tmp_path / "site" / "app.js").read_text("utf-8")
    assert "applyFilters" in script
    assert "renderInspector" in script
    assert "popstate" in script
    assert "inspectorPanel.inert" in script
    assert "Open Evidence" in script
    assert "data-inspect-index" in text
    assert '<tr tabindex="0" role="button"' not in text

    manifest = json.loads((tmp_path / "site" / "browser-manifest.json").read_text("utf-8"))
    assert manifest["interface"] == "research-observatory-v4"


def test_h2_browser_rejects_generic_failure(tmp_path):
    value = matrix()
    value["lanes"][0]["disposition"] = "FAIL"
    source = tmp_path / "matrix.json"
    source.write_text(json.dumps(value), "utf-8")
    with pytest.raises(ValueError, match="generic disposition"):
        render_qualification_browser(source, tmp_path / "site")


def test_h2_public_allowlist_tracks_frozen_matrix():
    from pathlib import Path
    from cvsubstrate.publication.audit import _qualification_public_allowlist

    root = Path(__file__).resolve().parents[1]
    value = json.loads((root / "qualification/h2/qualification-matrix.json").read_text("utf-8"))
    allowed = _qualification_public_allowlist(root)
    expected = {
        lane["evidence"]
        for lane in value["lanes"]
        if lane["evidence"].startswith("qualification/")
    }
    assert expected <= allowed
    assert "qualification/h2/browser/index.html" in allowed
    assert "qualification/h2/browser/qualification-matrix.json" in allowed
