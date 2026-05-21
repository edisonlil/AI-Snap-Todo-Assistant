---
name: chattodo-cross-packager
description: Bootstrap Chattodo packaging on clean Windows or macOS machines. Use when Codex needs to fetch this repository from `git clone` or a `.zip` source archive, install missing Git/Python/Node toolchains, create an isolated build workspace, and produce Windows `onedir` or `onefile`, macOS Apple Silicon, macOS Intel, or macOS `universal2` build artifacts. Trigger on requests like "自动拉取项目打包", "从 zip 解压后打包", "git clone 后打 windows/mac/mac intel 包", or "在客户机自动安装依赖并出包".
---

# Chattodo Cross Packager

Use this skill when the user wants a repeatable packaging workflow for this repository on a machine that may have none of the usual prerequisites installed.

## Workflow

1. Choose the host OS entry script.
   Windows: `scripts/package_chattodo.ps1`
   macOS: `scripts/package_chattodo.sh`
2. Choose the source mode.
   `git`: clone from a repository URL, optionally checkout a ref.
   `zip`: use a local `.zip` archive or a remote `.zip` URL.
3. Choose the packaging target that matches the host OS.
   Windows: `windows-onedir`, `windows-onefile`
   macOS: `macos-arm64`, `macos-x86_64`, `macos-universal2`
4. Run the entry script with a dedicated workspace path.
5. Read the final artifact path printed by the helper and return that path to the user.

## Rules

- Do not assume Git, Python, Node, or the repository checkout already exist.
- Prefer the wrapper script for the current host OS; it bootstraps missing tools before calling the Python orchestrator.
- Install Node only when `--with-website` is requested. The current desktop packaging flow does not require Node by default.
- Do not promise cross-compilation.
  Windows targets must be built on Windows.
  macOS targets must be built on macOS.
- For `macos-x86_64`, require an Intel Mac or an Apple Silicon machine already running an `x86_64` Python toolchain under Rosetta.
- For `macos-universal2`, warn that success depends on universal2-compatible Python and wheels.

## Entry Points

### Windows

Use:

```powershell
.\chattodo-cross-packager\scripts\package_chattodo.ps1 --source-method git --repo-url https://example.com/repo.git --target windows-onefile --workspace C:\builds\chattodo
```

Or:

```powershell
.\chattodo-cross-packager\scripts\package_chattodo.ps1 --source-method zip --zip-path C:\drop\AI-Snap-Todo-Assistant.zip --target windows-onedir --workspace C:\builds\chattodo
```

### macOS

Use:

```bash
./chattodo-cross-packager/scripts/package_chattodo.sh --source-method git --repo-url https://example.com/repo.git --target macos-arm64 --workspace ~/builds/chattodo
```

Or:

```bash
./chattodo-cross-packager/scripts/package_chattodo.sh --source-method zip --zip-path ~/Downloads/AI-Snap-Todo-Assistant.zip --target macos-x86_64 --workspace ~/builds/chattodo
```

## Arguments

- `--source-method git|zip`: required.
- `--repo-url <url>`: required for `git`.
- `--ref <git-ref>`: optional for `git`.
- `--zip-path <path-or-url>`: required for `zip`.
- `--target <target>`: required.
- `--workspace <dir>`: required; the helper creates a timestamped build session under it.
- `--with-website`: optional; build the website with Node after bootstrapping Node.
- `--python <path>`: optional override for the bootstrap/runtime Python.
- `--clean`: optional; remove the target session directory if it already exists.

## Resources

- Orchestrator: `scripts/package_chattodo.py`
- Windows bootstrap: `scripts/package_chattodo.ps1`
- macOS bootstrap: `scripts/package_chattodo.sh`
- Build matrix and constraints: `references/build-matrix.md`

## Reporting

- Return the exact artifact path produced by the helper.
- If bootstrap fails because the machine cannot install prerequisites automatically, return the blocking command and reason instead of guessing.
- If the requested target is incompatible with the host OS, stop and say so explicitly.
