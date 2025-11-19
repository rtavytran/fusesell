# Repository Guidelines

## Project Structure & Module Organization
Primary application code lives under `fusesell_local/`, broken into `stages/` for the pipeline steps, `utils/` for shared services, and `config/` for JSON defaults bundled with the wheel. The `fusesell.py` shim at the package root preserves legacy entry points while delegating to `fusesell_local.cli`. Distribution artefacts land in `build/`, `dist/`, and `fusesell.egg-info/` and should be ignored in reviews. Runtime data, logs, and the SQLite file accumulate in `fusesell_data/`; treat that folder as disposable and keep it out of commits. Automated scripts that weave FuseSell into RealtimeX flows reside in the sibling `../realtimex-flows/` project -- align interface changes across both repos.

## Build, Test, and Development Commands
Install development dependencies with `pip install -e .[dev]`. Produce release artefacts via `python -m build`. Run the full suite using `pytest fusesell_local/tests` after activating your virtualenv. For a CLI smoke test, execute `python fusesell.py --dry-run --openai-api-key dummy --org-id local --org-name "Local Test" --input-website https://example.com`.

## Coding Style & Naming Conventions
Adhere to PEP 8 using four-space indentation and keep lines near 100 characters. Use snake_case for functions (`load_team_settings`) and CapWords for classes (`FuseSellPipeline`). Preserve module docstrings, type hints, and logging patterns already present in `cli.py` and `pipeline.py`. Reuse helpers in `fusesell_local.utils` before introducing new abstractions, and update package exports when you expose new public APIs.

## Testing Guidelines
Place unit and integration tests in `fusesell_local/tests/test_<feature>.py`, mirroring the module under test. Leverage fixtures in `conftest.py` for in-memory configuration and data scaffolding. Add regression coverage whenever you modify pipeline stages, validators, or CLI arguments, and run targeted checks with `pytest -k <feature>` when iterating locally. Surface any unavoidable coverage gaps in the pull request description.

## Commit & Pull Request Guidelines
Write focused commits with imperative, Title Case subjects, mirroring history such as `Release 1.2.2` or `Restore Emoji Formatting In Documentation`. Reference issue IDs or external tickets in the body when relevant. Pull requests should summarise intent, list validation evidence (pytest output or screenshots), call out deployment steps, and mention downstream impacts on RealtimeX or other consumers.

## Security & Configuration Tips
Store secrets outside the repo using environment variables or files ignored under `fusesell_data/config/`. Purge sensitive exports from `fusesell_data/` before publishing branches. When introducing new configuration options, document safe defaults in `fusesell_local/config/*.json` and ensure CLI flags fail closed if required inputs are missing.

## RealtimeX Integration
RealtimeX is a comprehensive platform for creating, sharing, and discovering new agents and tools, aiming to be the ultimate AI environment for productivity and innovation. FuseSell powers RealtimeX sales automation flows, so validate behavioural changes end-to-end and keep release notes explicit about interface updates. After modifying CLI commands, pipeline outputs, or persistence formats, exercise the companion workflows in `../realtimex-flows/` and refresh the Markdown documentation in `../realtimex-flows/docs/` so agents continue to launch smoothly within RealtimeX.

