# Copilot Custom Review Instructions

## Repository Overview

**electrolux-ac-infrared** is a Home Assistant custom integration that encodes/decodes the
Electrolux portable AC infrared protocol and exposes it as a `climate` entity. It's built on
Home Assistant's `infrared` building-block integration (2026.4+): this repo only produces and
parses IR frames, it never talks to hardware or the network directly. Targets Python 3.14,
uses `uv` as the package manager and `prek` (a parallel pre-commit runner) for linting.

## Build, Test, and Lint Commands

| Task                                 | Command                    |
| ------------------------------------ | -------------------------- |
| Install dependencies / run a command | `uv run --dev <command>`   |
| Run the test suite                   | `uv run --dev pytest`      |
| Run lint, format, and type checks    | `uvx prek run --all-files` |
| Regenerate the lockfile              | `uv lock`                  |

Pre-commit hooks (ruff format + lint, pyrefly, yamlfmt, yamllint, codespell, tombi, mdformat,
markdownlint-cli2, actionlint, zizmor) must pass before every commit; they run through `prek`
with pinned versions in `.pre-commit-config.yaml` so results match CI.

## Project Layout

```text
custom_components/electrolux_ac_infrared/
  electrolux_ac.py    IR protocol encoder/decoder (ElectroluxAcCommand), no Home Assistant
                       dependency. Implements infrared_protocols.commands.Command.
  climate.py           The climate entity: HA climate semantics <-> ElectroluxAcCommand.
  config_flow.py       Config flow; selects the infrared emitter/receiver entities.
  const.py             Domain and shared constants.
  manifest.json        Integration metadata; version must match pyproject.toml.
  strings.json         Config flow / entity strings; translations/en.json must track it.
  translations/        Per-locale copies of strings.json.
  brand/               HACS brand assets (icons, logos).
tests/                 pytest suite using pytest-homeassistant-custom-component fixtures.
.pre-commit-config.yaml Hook definitions, pinned to match CI.
.github/workflows/      CI: Test (pytest, pre-commit) and Validate (hassfest, HACS).
```

## Review Checklist — What to Verify on Every PR

### Code Style and Quality

- Ruff and pyrefly config lives in `pyproject.toml`; per-rule ignores there are commented with
  *why*, not just *what*. Verify no lint or type-check violations are introduced, and that a
  new ignore comes with a similar rationale comment rather than a bare suppression.
- Public modules/classes/functions have a docstring (ruff's `D`/`DOC` rules apply; one-line
  docstrings are exempt from the stricter `DOC` (pydoclint) checks).
- Home Assistant platform setup callbacks (`async_setup_entry`, etc.) are `async def` even when
  nothing inside awaits — this is required by HA's callback signature, not a bug to "fix" by
  removing `async`.

### Protocol and Entity Correctness

- `electrolux_ac.py` is the single source of truth for the wire protocol. A change to frame
  encoding (`get_raw_timings`) needs a matching update to decoding (`from_raw_timings`) if the
  receive path should stay able to parse it, and vice versa.
- Device quirks mirrored by `climate.py` must stay intact unless the PR explicitly changes them:
  dry mode always runs fan at low; fan-only mode has no auto fan speed (falls back to low);
  changing fan/swing/temperature while off stores the setting instead of transmitting; a
  restart while off falls back to cool rather than the last-used mode.
- The entity is assumed-state (infrared is one-way). Don't add code that treats the climate
  entity's state as ground truth for the physical unit's actual state.
- This integration must not add direct hardware or network I/O. All IR transmission goes
  through the `infrared` building-block entities (`InfraredEmitterConsumerEntity` /
  `InfraredReceiverConsumerEntity`); flag any new dependency that isn't `infrared-protocols` or
  Home Assistant core.

### Testing

- New behavior needs a test; a bug fix needs a regression test.
- Tests use `pytest-homeassistant-custom-component` fixtures (see `tests/conftest.py`) rather
  than hand-rolled Home Assistant stubs.

### Versioning and Metadata

- `manifest.json`'s `version` and `pyproject.toml`'s `version` must match. If either changes,
  `uv.lock` must be regenerated (`uv lock`) in the same PR.
- If `strings.json` changes, `translations/en.json` should be updated to match in the same PR.
  Other locales don't need to track every change immediately.
- Versioning follows [ZeroVer](https://0ver.org/): a 0.y version bump carries no implicit
  stability guarantee either way.

### Git and CI

- This repo takes changes through pull requests, not direct pushes to `main`.
- Commit messages use imperative mood ("Add x", not "Added x").
- All CI checks must pass: the `pre-commit` job, the `test` job, and `Validate` (hassfest,
  HACS).

### Security

- No secrets or private keys committed (the `detect-private-key` hook helps, but review too).
- New dependencies should be justified and pinned appropriately in `pyproject.toml`.
- GitHub Actions workflows are checked by `actionlint` and `zizmor`; an `unpinned-uses` or
  similar finding needs either a pin or an explicit `zizmor: ignore[...]` comment explaining why.
