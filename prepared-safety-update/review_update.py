"""Read-only by default; --apply requires a stopped, unchanged target checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

PACKAGE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def inside(root, rel):
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe manifest path: {rel}")
    return path


def running_processes(target, changed):
    if os.name != "nt":
        raise RuntimeError("This review/apply utility requires Windows process inspection")
    result = subprocess.run([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    ], capture_output=True, text=True, timeout=30, check=True)
    rows = json.loads(result.stdout.strip() or "[]")
    if isinstance(rows, dict): rows = [rows]
    # Relative-script launches may not include their working directory. Include
    # known project script names rather than overlooking these processes.
    scripts = {p.name.lower() for p in target.glob("*.py")}
    scripts.update(Path(rel).name.lower() for rel in changed if rel.endswith(".py"))
    found = []
    for row in rows:
        if row["ProcessId"] == os.getpid(): continue
        command = (row.get("CommandLine") or "").lower()
        if not command:
            raise RuntimeError("A Python process command line could not be inspected; refusing deployment")
        if str(target).lower() in command or any(name in command for name in scripts):
            # Do not print full command lines, which may contain credentials.
            found.append(row["ProcessId"])
    return found


def replace_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".safety-update-", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=PACKAGE.parent)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    manifest = json.loads((PACKAGE / "update_manifest.json").read_text(encoding="utf-8"))
    conflicts = []
    for rel, entry in manifest.items():
        prepared = inside(PACKAGE / "source", rel)
        if digest(prepared) != entry["prepared_sha256"]:
            raise RuntimeError(f"Prepared artifact was modified after verification: {rel}")
        if digest(inside(target, rel)) != entry["original_sha256"]:
            conflicts.append(rel)
    processes = running_processes(target, manifest)
    print(f"Prepared files: {len(manifest)}")
    print(f"Running project Python process IDs: {processes or 'none'}")
    print(f"Source conflicts: {conflicts or 'none'}")
    if not args.apply:
        print("Read-only review complete. No files or processes changed.")
        return
    if processes or conflicts:
        raise RuntimeError("Deployment refused: stop project processes and review source conflicts first")
    backup = PACKAGE / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(parents=True)
    for rel, entry in manifest.items():
        path = inside(target, rel)
        if entry["original_sha256"] is not None:
            saved = inside(backup, rel)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
    applied = []
    try:
        for rel, entry in manifest.items():
            path = inside(target, rel)
            if digest(path) != entry["original_sha256"]:
                raise RuntimeError(f"Target changed during deployment: {rel}")
            replace_file(inside(PACKAGE / "source", rel), path)
            applied.append(rel)
    except Exception:
        for rel in reversed(applied):
            path = inside(target, rel)
            if manifest[rel]["original_sha256"] is None:
                path.unlink()
            else:
                replace_file(inside(backup, rel), path)
        raise
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Applied {len(applied)} files; backups: {backup}")
    print("No services started and no execution policy enabled.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Review/apply failed: {exc}", file=sys.stderr)
        sys.exit(1)
