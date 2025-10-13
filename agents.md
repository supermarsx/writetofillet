# Repository Guidelines

## Project Structure
- `src/writetofillet/` — CLI source (`cli.py`) and package init.
- `writetofillet.py` — legacy wrapper for backward compatibility.
- `tests/` — unit tests (pytest).
- `.github/workflows/` — CI for format, lint, test, build, release.
- `readme.md`, `license.md` — docs and license.

## Build, Test, Develop
- Run CLI: `writetofillet --help` (or `python -m writetofillet`)
- Local dev install: none required (stdlib). Optional tools: `pip install black ruff pytest pyinstaller`.
- Format: `black .`  | Lint: `ruff check .`  | Tests: `pytest -q`
- Build (single binary): `pyinstaller --onefile -n writetofillet src/writetofillet/cli.py`

## Coding Style
- Python 3.10+, 4‑space indents, PEP 8.
- `snake_case` for variables/functions; keep names explicit.
- Keep functions small; prefer pure helpers for generation/parsing.
- If adding tooling, keep configs in `pyproject.toml`.

## Testing
- Framework: `pytest`.
- Put tests under `tests/`, named `test_*.py`.
- Cover: size/times parsing, encoding selection, dictionary modes, pump modes, append vs write.
- Use `tmp_path` for filesystem tests; avoid large payloads.

## Commits & PRs
- Conventional Commits recommended: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- PRs: include description, rationale, examples, linked issues, and updated docs when behavior changes.

## Security & Ops
- Writes can be large. Default is append; use `--write-mode normal-write` to truncate.
- Prefer explicit `--encoding`; `--encoding auto` performs best‑effort detection.
- Limit sizes in CI/tests; avoid network or privileged paths.
