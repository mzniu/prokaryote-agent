# Copilot instructions for prokaryote-agent

## Big picture
- Product scope and V0.1 boundaries are defined in [docs/PRD.md](docs/PRD.md). Keep the “survival-first, minimal architecture” constraint.
- Architecture is a 3-layer, minimal design (storage → core modules → interface) described in [docs/概要设计.md](docs/概要设计.md).
- V0.1 focuses only on initialization, monitoring, repair, and local storage; **do not** introduce mutation/replication modules yet (they are V0.2+).

## Core components (V0.1)
- Initialization module: `ProkaryoteInit` loads config/backup, creates directories, sets baseline state.
- Monitoring module: `ProkaryoteMonitor` runs a 1s loop (threaded), checks process health, resources, file permissions, disk space, and emits abnormalities.
- Repair module: `ProkaryoteRepair` restores from local backups, verifies via monitor, and handles 3-failure emergency stop.
- External API is intentionally tiny: `init_prokaryote`, `start_prokaryote`, `stop_prokaryote`, `query_prokaryote_state`.

## Storage & data layout
- Local filesystem only. Default root is `./prokaryote_agent/` with `config/`, `backup/`, `log/` subfolders and JSON/TXT files.
- `config.json` drives intervals, thresholds, and repair limits; `config_backup.json` mirrors it for recovery.
- Logs are simple text via `logging`, with timestamps and module tags; retain ≥7 days.

## Conventions & constraints
- Favor Python standard library; optional `psutil` and `filelock` are allowed but not required.
- Keep V0.1 code small and readable (target ~500 lines for core logic).
- Avoid complex frameworks or heavy dependencies; the design expects direct function calls between modules.

## Developer workflows
- This repo currently contains design/PRD docs only; no build/test commands are defined yet.
- Use Python 3.8+; the design recommends 3.13 when available.

## When adding code
- Follow the module names and method responsibilities described in [docs/概要设计.md](docs/概要设计.md).
- Keep file/dir names consistent with the storage structure in the design to avoid breaking backups/logs.
- Any new interfaces should stay minimal and map cleanly to the V0.1 loop: init → monitor → repair → monitor.
