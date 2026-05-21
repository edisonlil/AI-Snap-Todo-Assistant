# Repository Guidelines

## Project Structure & Module Organization
Primary application code lives in `src/aica/`. Core entry and workflow modules include `main.py`, `overlay.py`, `toolbar.py`, `worker.py`, `config.py`, `prompts.py`, and `single_instance.py`. Supporting UI and Todo-related modules also live in `src/aica/`. Tests are in `tests/` and follow the `test_<module>.py` pattern, for example `test_overlay.py` and `test_todo_store.py`. Packaged assets are stored in `assets/`. Build metadata and PyInstaller specs are at the repo root: `aica.spec`, `aica_onefile.spec`, and `aica_version_info.txt`. Treat `build/`, `dist/`, `dist_onefile/`, and `__pycache__/` as generated output.

## Product Naming
The official customer-facing product name is `Chattodo`. Use `Chattodo` in product documentation, customer-facing copy, marketing text, and newly written UI text. Treat `AI Snap Todo Assistant` as a legacy descriptive repository name, not the official product name. Keep existing engineering identifiers such as `aica`, `AICA.app`, file paths, package names, and config directories unchanged unless a task explicitly requests a technical rename.

## Build, Test, and Development Commands
- `python .\run_aica.py`: run the app locally from source.
- `python -m compileall src\aica run_aica.py`: quick syntax and import smoke check.
- `pytest tests\test_overlay.py tests\test_compress.py tests\test_prompts.py tests\test_single_instance.py -q`: fast verified regression suite.
- `pytest -q`: run the full test suite when touching shared logic.
- `powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1`: build the Windows `onedir` package.
- `powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile.ps1`: build the single-file executable.

## Coding Style & Naming Conventions
Use 4-space indentation and keep code PEP 8 aligned. Prefer type hints where practical. Use `snake_case` for functions, files, and variables; use `PascalCase` for Qt widgets, dialogs, and dataclasses. Keep internal code and comments in English unless matching existing localized content. Keep user-facing UI text in Simplified Chinese for consistency. All source files, QML files, tests, and generated text templates must be saved as UTF-8; when reading or writing text in code, prefer explicitly passing `encoding="utf-8"` unless the API already guarantees UTF-8. Avoid mixed encodings, manual transcoding, or editor settings that may rewrite Chinese text as mojibake. Prefer small helper functions over long event handlers, and keep PyQt signal wiring explicit in `main.py`.

## Testing Guidelines
Use `pytest` for all tests. Add new tests beside related modules under `tests/`, named `test_<feature>.py`, with test functions named `test_<behavior>()`. Favor logic-level coverage over fragile GUI automation. When changing capture, prompt, or packaging flows, run the regression suite before submitting.

## Commit & Pull Request Guidelines
Use short, imperative Chinese commit summaries with one theme per commit, such as `优化反馈面板` or `实现打包`. Pull requests should include a clear description, affected areas, test commands run, and screenshots or GIFs for UI changes. Call out packaging output changes explicitly when modifying spec files, icons, or version metadata.

## Security & Configuration Tips
Do not commit real API keys. Runtime configuration belongs in `~/.aica/config.json`; keep the default `api_key` empty in code. Document any new config fields in `README.md`. Prompt and feedback data are stored under `~/.aica/`, so changes to those formats should preserve backward compatibility where possible.
