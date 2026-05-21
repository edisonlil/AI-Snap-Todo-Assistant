#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


WINDOWS_TARGETS = {"windows-onedir", "windows-onefile"}
MACOS_TARGETS = {"macos-arm64", "macos-x86_64", "macos-universal2"}
REPO_MARKERS = ("run_aica.py", "requirements.txt", "scripts")


@dataclass(frozen=True)
class SessionPaths:
    root: Path
    source: Path
    output: Path
    downloads: Path
    venv: Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Chattodo packaging from git or zip.")
    parser.add_argument("--source-method", choices=("git", "zip"), required=True)
    parser.add_argument("--repo-url")
    parser.add_argument("--ref")
    parser.add_argument("--zip-path")
    parser.add_argument("--target", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--python", dest="python_executable")
    parser.add_argument("--with-website", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--session-name")
    return parser.parse_args(argv)


def host_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "other"


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    print(f"[run] {printable}")
    subprocess.run(command, cwd=str(cwd) if cwd else None, env=env, check=True)


def validate_request(args: argparse.Namespace) -> tuple[str, str]:
    host = host_platform()
    if host == "other":
        raise SystemExit("Unsupported host OS. Use Windows or macOS.")
    if args.target in WINDOWS_TARGETS and host != "windows":
        raise SystemExit("Windows targets must be built on Windows.")
    if args.target in MACOS_TARGETS and host != "macos":
        raise SystemExit("macOS targets must be built on macOS.")
    if args.target not in WINDOWS_TARGETS | MACOS_TARGETS:
        raise SystemExit(f"Unsupported target: {args.target}")

    python_arch = platform.machine().lower()
    if args.target == "macos-x86_64" and python_arch not in {"x86_64", "amd64"}:
        raise SystemExit(
            "macos-x86_64 packaging requires an x86_64 Python runtime. "
            "Run the macOS wrapper under Rosetta or use an Intel Mac."
        )
    if args.source_method == "git" and not args.repo_url:
        raise SystemExit("--repo-url is required when --source-method git is used.")
    if args.source_method == "zip" and not args.zip_path:
        raise SystemExit("--zip-path is required when --source-method zip is used.")
    return host, python_arch


def build_session_paths(workspace: Path, target: str, session_name: str | None, clean: bool) -> SessionPaths:
    workspace = workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    session = session_name or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{target}"
    root = workspace / session
    if clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    source = root / "source"
    output = root / "output"
    downloads = root / "downloads"
    venv = root / ".venv-packaging"
    for path in (source, output, downloads):
        path.mkdir(parents=True, exist_ok=True)
    return SessionPaths(root=root, source=source, output=output, downloads=downloads, venv=venv)


def acquire_source(args: argparse.Namespace, session: SessionPaths) -> Path:
    if args.source_method == "git":
        return clone_repo(args.repo_url, args.ref, session.source)
    return extract_zip_source(args.zip_path, session)


def clone_repo(repo_url: str, ref: str | None, source_dir: Path) -> Path:
    checkout = source_dir / "repo"
    run(["git", "clone", repo_url, str(checkout)])
    if ref:
        run(["git", "checkout", ref], cwd=checkout)
    return checkout


def extract_zip_source(zip_path: str, session: SessionPaths) -> Path:
    local_zip = materialize_zip(zip_path, session.downloads)
    extract_dir = session.source / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    print(f"[info] Extracting {local_zip} -> {extract_dir}")
    with zipfile.ZipFile(local_zip) as archive:
        archive.extractall(extract_dir)
    repo_root = find_repo_root(extract_dir)
    if repo_root is None:
        raise SystemExit(f"Could not find the Chattodo repo root inside extracted archive: {local_zip}")
    return repo_root


def materialize_zip(value: str, downloads_dir: Path) -> Path:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        target = downloads_dir / (Path(parsed.path).name or "source.zip")
        print(f"[info] Downloading {value} -> {target}")
        with urllib.request.urlopen(value) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        return target
    local = Path(value).expanduser().resolve()
    if not local.exists():
        raise SystemExit(f"Zip archive does not exist: {local}")
    return local


def find_repo_root(extract_dir: Path) -> Path | None:
    if is_repo_root(extract_dir):
        return extract_dir
    candidates = [path for path in extract_dir.rglob("run_aica.py") if path.is_file()]
    for candidate in candidates:
        root = candidate.parent
        if is_repo_root(root):
            return root
    return None


def is_repo_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in REPO_MARKERS)


def create_venv(session: SessionPaths, python_executable: str | None) -> Path:
    bootstrap_python = python_executable or sys.executable
    run([bootstrap_python, "-m", "venv", str(session.venv)])
    venv_python = session.venv / ("Scripts" if host_platform() == "windows" else "bin") / (
        "python.exe" if host_platform() == "windows" else "python"
    )
    if not venv_python.exists():
        raise SystemExit(f"Virtual environment python not found: {venv_python}")
    return venv_python


def install_python_dependencies(repo_dir: Path, venv_python: Path) -> None:
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], cwd=repo_dir)
    run([str(venv_python), "-m", "pip", "install", "-r", "requirements-build.txt"], cwd=repo_dir)


def maybe_build_website(repo_dir: Path, with_website: bool, env: dict[str, str]) -> None:
    if not with_website:
        return
    website_dir = repo_dir / "website"
    package_json = website_dir / "package.json"
    if not package_json.exists():
        print("[warn] website/package.json is missing. Skipping website build.")
        return
    npm_command = "npm.cmd" if host_platform() == "windows" else "npm"
    run([npm_command, "ci"], cwd=website_dir, env=env)
    run([npm_command, "run", "build"], cwd=website_dir, env=env)


def build_desktop_target(repo_dir: Path, target: str, venv_python: Path, env: dict[str, str]) -> Path:
    if target == "windows-onedir":
        run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts\\build_exe.ps1",
                "-SkipInstall",
            ],
            cwd=repo_dir,
            env=env,
        )
        return repo_dir / "dist" / "AICA"
    if target == "windows-onefile":
        run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts\\build_onefile.ps1",
                "-SkipInstall",
            ],
            cwd=repo_dir,
            env=env,
        )
        return repo_dir / "dist" / "AICA.exe"

    build_command = ["bash", "scripts/build_macos_app.sh", "--skip-install"]
    if target == "macos-arm64":
        build_command.extend(["--target-arch", "arm64"])
    elif target == "macos-x86_64":
        build_command.extend(["--target-arch", "x86_64"])
    elif target == "macos-universal2":
        build_command.extend(["--target-arch", "universal2"])
    env = dict(env)
    env["PYTHON"] = str(venv_python)
    run(build_command, cwd=repo_dir, env=env)
    return repo_dir / "dist" / "AICA.app"


def build_env(venv_python: Path) -> dict[str, str]:
    env = dict(os.environ)
    scripts_dir = venv_python.parent
    env["VIRTUAL_ENV"] = str(scripts_dir.parent)
    env["PATH"] = str(scripts_dir) + os.pathsep + env.get("PATH", "")
    return env


def publish_artifact(artifact_path: Path, output_dir: Path, target: str, source_method: str) -> Path:
    if not artifact_path.exists():
        raise SystemExit(f"Expected build artifact was not produced: {artifact_path}")
    destination = output_dir / artifact_path.name
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    if artifact_path.is_dir():
        shutil.copytree(artifact_path, destination)
    else:
        shutil.copy2(artifact_path, destination)
    metadata = {
        "target": target,
        "artifact": str(destination),
        "source_method": source_method,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    (output_dir / "build-result.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return destination


def main() -> int:
    args = parse_args()
    host, python_arch = validate_request(args)
    print(f"[info] Host OS: {host}")
    print(f"[info] Python arch: {python_arch}")

    session = build_session_paths(
        Path(args.workspace),
        args.target,
        args.session_name,
        args.clean,
    )
    print(f"[info] Session root: {session.root}")

    repo_dir = acquire_source(args, session)
    print(f"[info] Repo root: {repo_dir}")

    venv_python = create_venv(session, args.python_executable)
    print(f"[info] Venv python: {venv_python}")

    install_python_dependencies(repo_dir, venv_python)
    env = build_env(venv_python)
    maybe_build_website(repo_dir, args.with_website, env)
    built_artifact = build_desktop_target(repo_dir, args.target, venv_python, env)
    final_artifact = publish_artifact(built_artifact, session.output, args.target, args.source_method)

    print(f"[done] Final artifact: {final_artifact}")
    print(f"[done] Session output: {session.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
