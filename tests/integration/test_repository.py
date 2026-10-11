"""Release guards must catch private tracked files and incomplete distributions."""

import importlib.util
import io
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "tools/check_repository.py"
SPEC = importlib.util.spec_from_file_location("repository_checks", SCRIPT)
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


def test_ignored_but_tracked_file_is_still_a_candidate(tmp_path):
    if not shutil.which("git"):
        pytest.skip("Git is needed for tracked-file behavior")

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    (tmp_path / ".gitignore").write_text(".env\nlocal_data/\n")
    (tmp_path / ".env").write_text("LOCAL_SETTING=example\n")
    (tmp_path / "local_data").mkdir()
    (tmp_path / "local_data/private.md").write_text("Local notes\n")
    git("add", "-f", ".env")
    names = checks.public_files(tmp_path)
    assert ".env" in names
    assert "local_data/private.md" not in names
    assert checks.private_path(".env")
    assert not checks.private_path(".env.example")
    assert checks.private_path(".env.example", archive=True)


def test_wheel_requires_metadata_and_rejects_private_files(tmp_path):
    path = tmp_path / "sdk.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("zk_rfid.py", "# SDK\n")
        archive.writestr("sdk.dist-info/METADATA", "License-Expression: MIT\n")
        archive.writestr("sdk.dist-info/licenses/LICENSE", "MIT License\n")
    assert checks.check_archive(path) == []
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("docs/.env.production", "LOCAL_SETTING=example\n")
    issues = checks.check_archive(path)
    assert any("private file" in issue for issue in issues)
    assert any("unexpected wheel file" in issue for issue in issues)


def test_source_archive_checks_assets_and_does_not_follow_links(tmp_path):
    path = tmp_path / "sdk.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("sdk/src/zk_rfid.py")
        data = b"# SDK\n"
        member.size = len(data)
        archive.addfile(member, io.BytesIO(data))
        link = tarfile.TarInfo("sdk/private")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../private"
        archive.addfile(link)
    issues = checks.check_archive(path)
    assert any("tag-memory.svg" in issue for issue in issues)
    assert any("unexpected archive link" in issue for issue in issues)


def test_link_visibility_and_secret_values_are_not_printed(tmp_path):
    (tmp_path / "private.md").write_text("not public\n")
    issues = checks.link_issues("README.md", "[notes](private.md)", {"README.md"}, tmp_path)
    assert any("missing public link target" in issue for issue in issues)
    token = "ghp_" + "x" * 36
    issues = checks.content_issues("example.py", token.encode())
    assert issues and token not in " ".join(issues)
    assert checks.content_issues("example.md", "\u0111\u1ecdc".encode())
