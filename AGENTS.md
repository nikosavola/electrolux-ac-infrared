# AGENTS.md

Home Assistant custom integration that encodes/decodes the Electrolux portable AC infrared
protocol and exposes it as a `climate` entity, built on the `infrared` building block
integration (Home Assistant 2026.4+). See [README.md](README.md) for what it does and
[CONTRIBUTING.md](CONTRIBUTING.md) for human-oriented setup and PR guidelines; this file is
the quick reference for coding agents.

## Setup and commands

This project uses [uv](https://docs.astral.sh/uv/); there's no manual virtualenv step.

```bash
uv run --dev pytest              # run the test suite
uvx prek run --all-files         # lint, format, and type-check (ruff, pyrefly, ...)
```

`prek` (a [pre-commit](https://pre-commit.com) drop-in replacement) runs the same hook
versions locally and in CI, defined in `.pre-commit-config.yaml`. Don't run `ruff` or
`pyrefly` directly with ad hoc flags; use `prek` so the configured versions and args match CI.

## Code layout

- `custom_components/electrolux_ac_infrared/electrolux_ac.py`: the IR protocol encoder/decoder
  (`ElectroluxAcCommand`), independent of Home Assistant. Implements
  `infrared_protocols.commands.Command`.
- `climate.py`: the `climate` entity, translating HA's climate semantics to/from
  `ElectroluxAcCommand`.
- `config_flow.py`: config flow, picks the `infrared` emitter/receiver entities.
- `const.py`: domain and shared constants.
- Tests live in `tests/`, using
  [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
  fixtures. New behavior needs a test; a bug fix needs a regression test.

## Conventions

- Ruff and pyrefly config live in `pyproject.toml`; per-rule ignores there are commented with
  *why*, not just *what* — read them before disabling a rule elsewhere.
- Keep `strings.json` and `translations/en.json` in sync when either changes; other locales
  don't need to track every change immediately.
- `manifest.json`'s `version` and `pyproject.toml`'s `version` must match, and `uv.lock` must
  be regenerated (`uv lock`) after either changes.
- Versioning follows [ZeroVer](https://0ver.org/): no stability guarantee is implied by the
  version number, so don't treat a 0.y bump as inherently breaking or non-breaking.

## Before opening a pull request

- `uv run --dev pytest` and `uvx prek run --all-files` both pass.
- Commits are atomic (one logical change each) with an imperative-mood message.
- This repo takes changes through pull requests, not direct pushes to `main`.
