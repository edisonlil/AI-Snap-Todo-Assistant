# Build Matrix

## Host to target mapping

| Host OS | Supported targets | Notes |
| --- | --- | --- |
| Windows | `windows-onedir`, `windows-onefile` | Uses `scripts/build_exe.ps1` or `scripts/build_onefile.ps1` inside the fetched repo. |
| macOS Apple Silicon | `macos-arm64`, `macos-universal2` | `macos-x86_64` requires an `x86_64` Python toolchain under Rosetta. |
| macOS Intel | `macos-x86_64`, `macos-universal2` | Native path for Intel `.app` output. |

## Source modes

### `git`

- Requires `--repo-url`.
- Accepts optional `--ref`.
- Clones into a timestamped workspace session.

### `zip`

- Requires `--zip-path`.
- Accepts a local archive path or an `http(s)` URL.
- Downloads the archive first when the value is a URL.
- Auto-detects the real repo root after extraction.

## Tool bootstrap policy

### Windows

- Install Git with `winget` when missing.
- Install Python 3.11 with `winget` when missing.
- Install Node LTS with `winget` only when `--with-website` is requested.

### macOS

- Install Homebrew when missing.
- Install Git with Homebrew when missing.
- Install Python 3.11 with Homebrew when missing.
- Install Node with Homebrew only when `--with-website` is requested.

## Artifact locations

The helper copies the built artifact into:

`<workspace>/<session-name>/output/`

Expected output names:

- `windows-onedir`: `AICA/`
- `windows-onefile`: `AICA.exe`
- `macos-arm64`: `AICA.app`
- `macos-x86_64`: `AICA.app`
- `macos-universal2`: `AICA.app`

## Example commands

### Windows from git

```powershell
.\chattodo-cross-packager\scripts\package_chattodo.ps1 --source-method git --repo-url https://github.com/example/AI-Snap-Todo-Assistant.git --ref main --target windows-onefile --workspace C:\builds\chattodo
```

### Windows from zip

```powershell
.\chattodo-cross-packager\scripts\package_chattodo.ps1 --source-method zip --zip-path C:\drop\AI-Snap-Todo-Assistant.zip --target windows-onedir --workspace C:\builds\chattodo
```

### macOS arm64 from git

```bash
./chattodo-cross-packager/scripts/package_chattodo.sh --source-method git --repo-url https://github.com/example/AI-Snap-Todo-Assistant.git --target macos-arm64 --workspace ~/builds/chattodo
```

### macOS Intel from zip

```bash
./chattodo-cross-packager/scripts/package_chattodo.sh --source-method zip --zip-path ~/Downloads/AI-Snap-Todo-Assistant.zip --target macos-x86_64 --workspace ~/builds/chattodo
```
