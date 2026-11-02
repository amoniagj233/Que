import hashlib
import json
import sys
from pathlib import Path

import pytest

import review_update as update


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    package, target = tmp_path / "package", tmp_path / "target"
    (package / "source").mkdir(parents=True)
    target.mkdir()
    manifest = {}
    for name in ("first.py", "second.py"):
        (target / name).write_text("original", encoding="utf-8")
        (package / "source" / name).write_text("prepared", encoding="utf-8")
        manifest[name] = dict(original_sha256=update.digest(target / name),
                              prepared_sha256=update.digest(package / "source" / name))
    (package / "update_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(update, "PACKAGE", package)
    monkeypatch.setattr(update, "running_processes", lambda *args: [])
    monkeypatch.setattr(sys, "argv", ["review_update.py", "--target", str(target), "--apply"])
    return package, target


def test_apply_refuses_running_services(prepared, monkeypatch):
    package, target = prepared
    monkeypatch.setattr(update, "running_processes", lambda *args: [123])
    with pytest.raises(RuntimeError, match="Deployment refused"):
        update.main()
    assert (target / "first.py").read_text() == "original"
    assert not (package / "backups").exists()


def test_apply_refuses_source_drift(prepared):
    _, target = prepared
    (target / "first.py").write_text("user edits", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Deployment refused"):
        update.main()
    assert (target / "first.py").read_text() == "user edits"


def test_failed_copy_rolls_back_completed_replacements(prepared, monkeypatch):
    package, target = prepared
    original = update.replace_file
    def fail_second(source, dest):
        if source == package / "source" / "second.py":
            raise OSError("simulated failed write")
        original(source, dest)
    monkeypatch.setattr(update, "replace_file", fail_second)
    with pytest.raises(OSError, match="simulated failed write"):
        update.main()
    assert (target / "first.py").read_text() == "original"
    assert (target / "second.py").read_text() == "original"


def test_default_review_does_not_change_target(prepared, monkeypatch):
    _, target = prepared
    monkeypatch.setattr(sys, "argv", ["review_update.py", "--target", str(target)])
    update.main()
    assert (target / "first.py").read_text() == "original"


def test_apply_verifies_artifact_hash(prepared):
    package, target = prepared
    (package / "source" / "first.py").write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact was modified"):
        update.main()
    assert (target / "first.py").read_text() == "original"


def test_manifest_cannot_escape_target(tmp_path):
    with pytest.raises(ValueError, match="Unsafe manifest path"):
        update.inside(tmp_path, "../outside.py")
