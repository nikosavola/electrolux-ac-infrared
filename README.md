# electrolux-ir-talk

Home Assistant oppii puhumaan Electroluxia: Oma integraatio ilmastointilaitteelle, jota ohjataan vain infrapunalla

Flash talk (in Finnish) about the [Electrolux AC Infrared](https://github.com/nikosavola/electrolux-ac-infrared)
integration, for Home Assistant Community Day in Helsinki. The slides are published at
<https://nikosavola.github.io/electrolux-ac-infrared/>.

A [Typst](https://typst.app) + [Touying](https://github.com/touying-typ/touying) deck using the `cycler` theme from
[typst-touying-template](https://github.com/nikosavola/typst-touying-template). Edit `main.typ`, and add references to
`refs.bib` to cite them with `@key`; they show up as footnotes on the slide. The PDF that `just build` writes to
`build/` is what gets presented.

## Development

```sh
just build        # compile main.typ to build/
just watch        # recompile on save
just preview      # render each slide to build/preview-*.png
just build-pptx   # optional PPTX export (one image per slide)
just pre-commit   # run all hooks
just agent-skills # add Typst/Touying skills for coding agents under .agents/skills
```

Requires [Typst](https://typst.app), [`just`](https://github.com/casey/just), and [`prek`](https://github.com/j178/prek)
for the hooks. The optional `build-pptx` also needs [`uv`](https://docs.astral.sh/uv/).

## Updating the template

This project was generated with [Copier](https://copier.readthedocs.io). To pull in later theme and tooling fixes:

```sh
uvx copier update
```

Copier only replays upstream changes made since this project was generated, so your slides are kept.
