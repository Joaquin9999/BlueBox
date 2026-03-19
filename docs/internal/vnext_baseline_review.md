# BlueBox vNext Baseline Review (Phase 0)

Date: 2026-03-19
Branch: `phase/0-vnext-baseline`

## Current command behavior checked

- `bluebox start`: available, prints onboarding and current command groups.
- `bluebox init`: interactive and flag-driven mode working.
- `bluebox status`: supports active-case resolution when path is omitted.
- `bluebox project`: supports `show`, `set`, `list`, `clear`, `prune-missing`.
- `bluebox tools`: supports `list`, `check`, `install` with dry-run default.

## Key modules identified

- CLI entrypoints: `bluebox/cli/app.py`
- Workspace creation: `bluebox/core/workspace_builder.py`
- Case model/required structure: `bluebox/core/case_model.py`
- Initialization from artifacts: `bluebox/core/init_service.py`
- Template rendering: `bluebox/core/template_renderer.py`
- Tool catalog/install logic: `bluebox/core/tools_catalog.py`, `bluebox/core/tools_service.py`

## Risks before vNext refactor

1. Existing case structure (`original/working/derived/...`) differs from vNext target (`challenge/work/agent/memory/output`).
2. Several commands currently depend on legacy metadata paths (`meta/*`, `notes/*`, `.codex/*`).
3. Backward compatibility needs adapter logic while introducing vNext structure.
4. Tooling profiles currently differ from vNext required profile set (`forensics-core`, `pcap`, `ctf-blue`, `all`).

## Strategy

- Introduce vNext workspace bootstrap and case layout first.
- Keep current commands operational via compatibility fallbacks.
- Migrate progressively with focused commits and targeted tests.
