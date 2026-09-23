# Default to listing available recipes
[private]
default:
    @just --list

# A generated project builds main.typ; the template repo itself builds its demo deck.
DECK := env("DECK", if path_exists("main.typ") == "true" { "main.typ" } else { "example/showcase.typ" })
BUILD_DIR := "build"
DECK_NAME := file_stem(DECK)
SITE_PDF := env("SITE_PDF", DECK_NAME + ".pdf")
SITE_TITLE := env("SITE_TITLE", DECK_NAME)
FMT_PATHS := "theme " + DECK + if path_exists("example") == "true" { " example" } else { "" }

# Keep in sync with the typstyle hook's args in .pre-commit-config.yaml.
LINE_WIDTH := "100"

# `just` runs recipes from the justfile's directory, so `--root .` and `--font-path fonts` always resolve.

# --- Build ---

# Compile the deck to build/
[group('build')]
build:
    mkdir -p {{ BUILD_DIR }}
    typst compile --root . --font-path fonts {{ DECK }} {{ BUILD_DIR }}/{{ DECK_NAME }}.pdf

# Recompile the deck on every save
[group('build')]
watch:
    mkdir -p {{ BUILD_DIR }}
    typst watch --root . --font-path fonts {{ DECK }} {{ BUILD_DIR }}/{{ DECK_NAME }}.pdf

# Render every slide to a PNG in build/ for a quick visual check
[group('build')]
preview: build
    typst compile --root . --font-path fonts {{ DECK }} {{ BUILD_DIR }}/preview-{0p}.png --format png --ppi 150

# Optional PPTX export, one full-slide image per slide (not editable text)
[group('build')]
build-pptx:
    mkdir -p {{ BUILD_DIR }}
    uvx touying@0.14.4 compile --root . --font-paths fonts --format pptx --ppi 200 --output {{ BUILD_DIR }}/{{ DECK_NAME }}.pptx {{ DECK }}

# Build the PDF plus an index.html that shows it, for GitHub Pages
[group('build')]
site: build
    mkdir -p {{ BUILD_DIR }}/site
    cp {{ BUILD_DIR }}/{{ DECK_NAME }}.pdf {{ BUILD_DIR }}/site/{{ SITE_PDF }}
    printf '%s\n' '<!doctype html>' '<meta charset="utf-8">' \
        '<meta name="viewport" content="width=device-width, initial-scale=1">' \
        '<title>{{ SITE_TITLE }}</title>' \
        '<style>html,body{margin:0;height:100%}object{display:block;width:100%;height:100%}</style>' \
        '<object data="{{ SITE_PDF }}" type="application/pdf">' \
        '<p><a href="{{ SITE_PDF }}">Open the slides (PDF)</a></p>' \
        '</object>' > {{ BUILD_DIR }}/site/index.html

# Remove build artifacts
[confirm]
[group('build')]
clean:
    rm -rf {{ BUILD_DIR }}

# --- Lint & format ---

# Reformat all Typst sources in place
[group('lint')]
format:
    typstyle -i --line-width {{ LINE_WIDTH }} {{ FMT_PATHS }}

# Check formatting without modifying files
[group('lint')]
format-check:
    typstyle --check --line-width {{ LINE_WIDTH }} {{ FMT_PATHS }}

# Run pre-commit hooks against all files
[group('lint')]
pre-commit:
    prek run -a

# --- Setup ---

# Install pre-commit hooks
[group('setup')]
pre-commit-install:
    prek install

# Add (or init) the Typst/Touying agent skills as git submodules under .agents/
[group('setup')]
agent-skills:
    #!/usr/bin/env sh
    set -eu
    sub() {
        if git ls-files --stage -- "$2" | grep -q '^160000'; then
            git submodule update --init "$2"
        else
            # GitHub's "Use this template" keeps .gitmodules but drops the gitlinks.
            rmdir "$2" 2>/dev/null || true
            git submodule add --force "$1" "$2"
        fi
    }
    sub https://github.com/apcamargo/typst-skills .agents/vendor/typst-skills
    sub https://github.com/touying-typ/seaslides .agents/vendor/seaslides
    mkdir -p .agents/skills .claude
    ln -sfn ../vendor/typst-skills/typst-author .agents/skills/typst-author
    ln -sfn ../vendor/typst-skills/touying-author .agents/skills/touying-author
    ln -sfn ../vendor/seaslides/skills/seaslides-typst-slides-skill .agents/skills/seaslides-typst-slides-skill
    ln -sfn ../.agents/skills .claude/skills
