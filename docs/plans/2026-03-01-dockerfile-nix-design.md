# Dockerfile with Nix Base Image

## Purpose

Dual-purpose container image for CI/CD reproducibility and contributor onboarding.
Uses the existing `flake.nix` as the single source of truth for all system dependencies.

## Base Image

`nixos/nix:2.28.3` — pinned for reproducibility, updated intentionally.

## Build Strategy

Nix dev shell closure is pre-built at image build time (`nix develop --command true`).
Python dependencies are pre-installed via `uv sync --frozen` into `/opt/venv`.
Two-layer caching: flake changes (rare, expensive) are separated from Python dep changes (occasional, cheap).

## Image Layout

```
nixos/nix:2.28.3
├── /etc/nix/nix.conf          flakes enabled
├── /nix/store/...             pre-built dev shell closure
├── /opt/venv/                 pre-installed Python deps
├── /build/flake.nix           flake source for nix develop
├── /build/flake.lock
└── /workspace/                mount point for project source
```

## Usage

```bash
# Interactive dev shell
docker build -t glinet-re .
docker run -it --rm -v "$PWD:/workspace" glinet-re

# CI: run tests
docker run --rm -v "$PWD:/workspace" glinet-re uv run pytest

# CI: run analysis script
docker run --rm -v "$PWD:/workspace" glinet-re uv run python3 scripts/analyze_uboot.py
```

## Key Decisions

- **ENTRYPOINT wraps `nix develop`** so all Nix tools are on PATH for any command.
- **`CMD ["bash"]`** gives contributors an interactive shell by default.
- **`UV_PROJECT_ENVIRONMENT=/opt/venv`** decouples the venv from the working directory.
- **`--frozen`** ensures uv uses the lockfile exactly, no network resolution at build time.
- **Aggressive `.dockerignore`** allowlists only the four files the Dockerfile COPYs.
- **No docker-compose** — single container, no services.
- **No multi-arch manifest** — build natively on the target architecture.

## Nix Container Compatibility

Two FHS issues discovered during testing:

1. **Native binaries** — pip-installed ELF binaries (e.g. `ruff`, `mypy`) ship with FHS dynamic linker paths that don't exist in nix containers. Solution: move native binary tools to `flake.nix`, keep only pure Python packages in `pyproject.toml`. Nix handles binaries, uv handles Python libraries.

2. **Script shebangs** — `#!/bin/bash` doesn't work since `/bin/bash` doesn't exist. All scripts must use `#!/usr/bin/env bash`. The container has `/usr/bin/env` symlinked to nix coreutils.

## Platform

Builds for `x86_64-linux` or `aarch64-linux` depending on host Docker engine.
The flake supports both and adds `rkdeveloptool` on Linux automatically.
