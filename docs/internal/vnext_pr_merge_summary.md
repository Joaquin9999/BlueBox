# BlueBox vNext — PR Merge Summary

## Title
`feat: complete vNext CLI UX, workspace model, and tooling profiles`

## What this PR delivers
This PR completes the vNext implementation roadmap across workspace structure, safer case creation, UX command layer, onboarding, active-case management, summaries/handoffs, progress scoring, and tooling profiles.

## Scope by phase

### Phase 0 — Baseline and branch prep
- Added baseline review: `docs/internal/vnext_baseline_review.md`
- Kept vNext roadmap/spec docs excluded from version control as requested.

### Phase 1 — Workspace + templates
- Standard top-level folders aligned to vNext:
  - `inbox/`, `cases/`, `exports/`, `profiles/`, `tools/`
- Case creation now targets `cases/<case-name>/`
- Added vNext templates:
  - `case.yaml`
  - `challenge/{source_ref.txt,manifest.json,hashes.json}`
  - `agent/{context.md,prompt.md,handoff.md}`
  - `memory/log.md`
  - `output/{writeup.md,writeup_final.md,final_flag.txt}`

### Phase 2 — Safer case creation
- Added `bluebox new` with explicit evidence modes:
  - `reference-only` (default)
  - `lightweight-copy`
  - `full-copy`
- Added path safety checks:
  - rejects invalid base/artifacts combinations
  - prevents unsafe nesting / workspace contamination cases

### Phase 3 — Default prompt rollout
- Shipped default vNext prompt template to `agent/prompt.md` on case creation.

### Phase 4 — Active case/session improvements
- Extended `.bluebox/` state:
  - `active_case.txt`
  - `recent_cases.json`
  - `settings.yaml`
- Added `cases` UX group:
  - `cases list/current/use/open/clear/archive/clone`
- Added short aliases:
  - `use`, `current`, `open`

### Phase 5 — Product-style command layer
- Added UX aliases while preserving technical commands:
  - `check -> validate`
  - `inspect -> classify`
  - `run -> solve`
  - `info -> status` (now enriched)
  - `report -> finalize`

### Phase 6 — Onboarding and operational UX
- Added `wizard`:
  - verifies environment basics
  - bootstraps standard folders
  - optional import into `inbox/` via `--import-source` and `--import-name`
  - optional case creation and next-step guidance
- Added `next` for state-aware next-action suggestions
- Added `home` dashboard view
- Enriched `info` output with:
  - progress score
  - completed/pending workflow dimensions
  - report count
  - active tool profile
  - recommended next action

### Phase 7 — Summaries and handoff
- Added `handoff` command:
  - generates concise handoff summary
  - writes `agent/handoff.md` by default
- Added `summary` command:
  - compact human-readable case summary
- Added `summarize` command:
  - converts large file outputs into compact markdown reports under `work/reports/`

### Phase 8 — Tooling profiles completion
- Expanded tool catalog and profile model to include required profiles:
  - `base`, `forensics-core`, `pcap`, `windows-dfir`, `memory`, `malware`, `ctf-blue`, `all`
- Added `tools profiles` command
- Improved install output summary (available/missing)
- Added tooling report emission to active case:
  - `work/reports/tooling_status.md`
- Added `setup --profile <name>` support (including `--profile all`)

## Backward compatibility
- Existing technical commands remain available:
  - `init`, `validate`, `classify`, `solve`, `status`, `finalize`, `project`, `tools`
- New UX commands are additive and mapped as aliases or wrappers.

## Operator-facing command additions
- `new`, `check`, `inspect`, `run`, `info`, `report`
- `cases ...` + `use/current/open`
- `wizard`, `next`, `home`
- `handoff`, `summary`, `summarize`
- `tools profiles`

## Validation performed
- Full test suite passes:
  - `pytest -q` => `44 passed`
- Smoke runs validated key flows:
  - safer `new` flow and active-case persistence
  - `cases` management flow
  - `wizard` onboarding and inbox import
  - `home/info/next` operational outputs
  - `handoff/summary/summarize`
  - tooling install summary + `tooling_status.md` report generation

## Suggested PR description (copy/paste)
This PR completes the BlueBox vNext roadmap with a safer workspace model, product-style command UX, stronger active-case/session handling, onboarding improvements, progress scoring, summary/handoff tooling, and expanded profile-based tooling installs.

It preserves backward compatibility for existing technical commands while adding a polished operator workflow (`new/check/inspect/run/info/report`, `cases`, `wizard`, `next`, `home`).

All changes are validated with `pytest -q` (44 passing) and smoke-tested for critical operational flows.

## Suggested merge notes
- Merge target: `main`
- Source branch: `phase/0-vnext-baseline`
- Post-merge recommendation:
  - run CI matrix
  - update release notes with the new command surface
