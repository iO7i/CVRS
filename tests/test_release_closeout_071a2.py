"""Publication-closeout regressions; no model or benchmark certification."""
from pathlib import Path
import json
import re
import tomllib

import pytest

from cvsubstrate.publication.audit import public_tree

ROOT = Path(__file__).resolve().parents[1]


def owner_pending_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "PUBLICATION.json").write_text("{}\n", encoding="utf-8")
    (source / "LICENSE").write_text("Owner review; no license grant.\n", encoding="utf-8")
    (source / "NOTICE").write_text("Independent project; no upstream affiliation.\n", encoding="utf-8")
    (source / "THIRD_PARTY_NOTICES.md").write_text("Retain third-party terms.\n", encoding="utf-8")
    return source


def test_public_preview_preserves_existing_attribution_notice(tmp_path):
    source = owner_pending_source(tmp_path)
    output = tmp_path / "public"
    public_tree(source, output, preview=True)
    assert (output / "NOTICE").is_file()
    assert (output / "NOTICE").read_bytes() == (source / "NOTICE").read_bytes()
    assert (output / "THIRD_PARTY_NOTICES.md").read_bytes() == (source / "THIRD_PARTY_NOTICES.md").read_bytes()


def test_source_and_wheel_license_files_are_explicit():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert set(project["license-files"]) == {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}
    assert all((ROOT / name).is_file() for name in project["license-files"])


def test_preview_does_not_approve_or_modify_owner_metadata(tmp_path):
    source = owner_pending_source(tmp_path)
    before = (source / "PUBLICATION.json").read_bytes()
    output = tmp_path / "public"
    result = public_tree(source, output, preview=True)
    assert result["audit"]["status"] == "BLOCK"
    assert {x["code"] for x in result["audit"]["findings"] if x["severity"] == "BLOCK"} == {"IDENTITY_PENDING", "LICENSE_PENDING"}
    assert (source / "PUBLICATION.json").read_bytes() == before
    assert (output / "PUBLICATION.json").read_bytes() == before
    assert json.loads((output / "PUBLIC_EXPORT.json").read_text())["mode"] == "OWNER_PREVIEW_NOT_PUBLISHABLE"


def test_nonpreview_still_blocks_missing_owner_approvals(tmp_path):
    source = owner_pending_source(tmp_path)
    with pytest.raises(ValueError, match="Owner identity/license"):
        public_tree(source, tmp_path / "public", preview=False)


def test_readme_local_targets_survive_public_export(tmp_path):
    output = tmp_path / "public"
    public_tree(ROOT, output, preview=True)
    readme = (output / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", readme)
    assert targets
    for target in targets:
        if "://" in target or target.startswith("#"):
            continue
        path = output / target.split("#", 1)[0]
        assert path.is_file(), target
