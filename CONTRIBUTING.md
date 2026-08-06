# Contributing

## Setup

This project uses [uv](https://docs.astral.sh/uv/). There is no manual virtualenv
step: `uv run` creates and syncs `.venv` from `pyproject.toml` on demand.

```bash
uv run --dev pytest
```

## Linting, formatting and type checking

Ruff and pyrefly aren't project dependencies; they run through
[pre-commit](https://pre-commit.com) hooks via
[`prek`](https://github.com/j178/prek), a drop-in pre-commit replacement, so the
same versions are used locally and in CI:

```bash
uvx prek run --all-files
```

Install it as a git hook so it runs automatically on every commit:

```bash
uvx prek install
```

## Before opening a pull request

- `uv run --dev pytest` and `uvx prek run --all-files` both pass.
- Keep commits atomic: one logical change per commit, with an imperative-mood
  message ("Add x", not "Added x" or "Adds x").
- New behavior gets a test; a bug fix gets a regression test.
- If you change `strings.json`, update `translations/en.json` to match, so the two
  don't drift apart. Other locales don't need to track every change immediately.

## Adding a translation

Copy `custom_components/electrolux_ac_infrared/translations/en.json` to
`<language-code>.json` in the same directory and translate the values, keeping the
keys identical. [Supported language codes are listed in Home Assistant's developer
docs](https://developers.home-assistant.io/docs/internationalization/translation/#getting-started).

## AI usage policy

Using AI tools to accelerate your workflow, whether for prototyping, writing tests, or
improving documentation, is **encouraged**.

However, as a contributor, you remain **fully responsible** for the code and content
you submit. Please ensure the following:

1. **No "AI slop"**: don't submit unreviewed, low-quality, or redundant AI-generated
   content.
1. **Verify and test**: all AI-generated code must be reviewed, tested, and verified
   to work as intended.
1. **Maintainability**: the content must be clear, idiomatic, and maintainable by a
   human.
