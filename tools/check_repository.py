"""Check public files, documentation links, and optional release archives."""

import argparse
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {
    ".git",
    ".codex",
    ".venv",
    "venv",
    "env",
    "local_data",
    "artifacts",
    "tmp",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "Protocol_ZK",
    "Protocol_NATION",
    "Mode_research",
    "vendor",
    "captures",
    "logs",
}
PRIVATE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".dll", ".exe", ".so", ".dylib", ".pyc"}
TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".md",
    ".json",
    ".yml",
    ".toml",
    ".html",
    ".css",
    ".svg",
}
# Distinctive Vietnamese letters; ASCII/Unicode prose still needs human review.
VIETNAMESE = re.compile(r"[\u0102\u0103\u0110\u0111\u01a0\u01a1\u01af\u01b0\u1ea0-\u1ef9]")
SECRETS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")


def private_path(name, *, archive=False):
    path = PurePosixPath(name)
    return (
        path.is_absolute()
        or ".." in path.parts
        or any(part in PRIVATE_DIRS for part in path.parts)
        or path.name.startswith("plan_agent")
        or (path.name.startswith(".env") and (archive or path.name != ".env.example"))
        or path.suffix.lower() in PRIVATE_SUFFIXES
        or any(part.endswith(".egg-info") for part in path.parts)
        and not archive
        or "dist" in path.parts
        and not archive
        or "build" in path.parts
    )


def public_files(root=ROOT):
    """Include tracked files even when an ignore rule now matches them."""
    if (root / ".git").exists():
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={root.as_posix()}",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            cwd=root,
            capture_output=True,
            check=True,
        )
        return sorted(set(result.stdout.decode("utf-8").rstrip("\0").split("\0")) - {""})
    # Source archives do not contain Git metadata.
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not private_path(p.relative_to(root).as_posix())
    )


def content_issues(name, data):
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    issues = []
    for number, line in enumerate(content.splitlines(), 1):
        if VIETNAMESE.search(line):
            issues.append(f"{name}:{number}: non-English text needs review")
        for label, pattern in SECRETS.items():
            if pattern.search(line):
                issues.append(f"{name}:{number}: possible {label} (value hidden)")
    return issues


def link_issues(name, content, names, root=ROOT):
    issues = []
    # Paths inside code samples are examples, not Markdown links.
    content = re.sub(r"```.*?```", "", content, flags=re.S)
    for match in LINK.finditer(content):
        target = urlsplit(match.group(1).strip("<>"))
        if target.scheme or target.netloc:
            continue
        path = (root / name).parent / unquote(target.path) if target.path else root / name
        path = path.resolve()
        try:
            relative = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            issues.append(f"{name}: link leaves repository")
            continue
        available = relative in names or any(n.startswith(relative + "/") for n in names)
        if not path.exists() or not available:
            issues.append(f"{name}: missing public link target {relative}")
        elif target.fragment.startswith("L") and target.fragment[1:].isdigit():
            if int(target.fragment[1:]) > len(path.read_text(encoding="utf-8").splitlines()):
                issues.append(f"{name}: source line exceeds {relative}")
    return issues


def check_archive(path):
    issues = []
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            contents = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
        if "zk_rfid.py" not in contents:
            issues.append(f"{path.name}: SDK module missing")
        for name in contents:
            if name != "zk_rfid.py" and not name.split("/")[0].endswith(".dist-info"):
                issues.append(f"{path.name}: unexpected wheel file {name}")
        metadata = [v for n, v in contents.items() if n.endswith(".dist-info/METADATA")]
        if len(metadata) != 1 or b"License-Expression: MIT" not in metadata[0]:
            issues.append(f"{path.name}: MIT metadata missing")
        if not any(n.endswith(".dist-info/licenses/LICENSE") for n in contents):
            issues.append(f"{path.name}: license file missing")
    else:
        with tarfile.open(path) as archive:
            contents = {}
            for member in archive.getmembers():
                if member.issym() or member.islnk():
                    issues.append(f"{path.name}: unexpected archive link {member.name}")
                elif member.isfile():
                    name = member.name.split("/", 1)[-1]
                    contents[name] = archive.extractfile(member).read()
        required = {
            "src/zk_rfid.py",
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "docs/assets/tag-memory.svg",
            "docs/assets/epc-write.svg",
            "docs/assets/wire-frame.svg",
            "examples/README.md",
            "web/zk-rfid-webserial.js",
            "web/zk_browser.py",
            "tests/runtime/runtime_checks.py",
            "compat/nation/LICENSE",
            "compat/nation/nrn.py",
        }
        for name in sorted(required - contents.keys()):
            issues.append(f"{path.name}: required source file missing: {name}")
    for name, data in contents.items():
        if private_path(name, archive=True):
            issues.append(f"{path.name}: private file {name}")
        issues.extend(content_issues(f"{path.name}/{name}", data))
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, help="Also inspect wheels and source archives here")
    args = parser.parse_args()
    names = set(public_files())
    issues = []
    for name in sorted(names):
        path = ROOT / name
        if not path.exists():  # A tracked deletion is reviewed through git diff.
            continue
        if private_path(name):
            issues.append(f"{name}: private file is a Git candidate")
        if path.is_symlink():
            issues.append(f"{name}: public symlink needs review")
            continue
        data = path.read_bytes()
        if path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".env.example"}:
            issues.extend(content_issues(name, data))
        if path.suffix == ".md":
            issues.extend(link_issues(name, data.decode("utf-8"), names))
    if args.dist:
        archives = sorted(args.dist.glob("*.whl")) + sorted(args.dist.glob("*.tar.gz"))
        if not any(p.suffix == ".whl" for p in archives) or not any(
            p.name.endswith(".tar.gz") for p in archives
        ):
            issues.append("Distribution directory must contain both a wheel and a source archive")
        for path in archives:
            issues.extend(check_archive(path))
    for issue in issues:
        print(issue)
    if issues:
        raise SystemExit(f"Repository check failed: {len(issues)} issue(s)")
    print(
        f"Repository check passed: {len(names)} public files; local links and common secrets checked"
    )
    if args.dist:
        print(f"Archive checks passed: {len(archives)} archives")


if __name__ == "__main__":
    main()
