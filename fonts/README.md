# Fonts

Vendored so decks compile the same everywhere, without depending on what's installed on the machine or CI image. Both
families come from [Google Fonts](https://github.com/google/fonts) as variable fonts and are licensed under the SIL Open
Font License 1.1, which allows bundling and redistribution. The license text for each is included here.

| Family      | File                                                    | Used for       |
| ----------- | ------------------------------------------------------- | -------------- |
| Roboto      | `Roboto[wdth,wght].ttf`, `Roboto-Italic[wdth,wght].ttf` | Text, headings |
| Roboto Mono | `RobotoMono[wght].ttf`                                  | Code           |

Math uses Typst's built-in New Computer Modern Math. Pass `--font-path fonts` when compiling; `just build` does this for
you.
