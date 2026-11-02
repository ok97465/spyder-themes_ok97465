# Theme sources

YAML theme trees for [ThemeWeaver](../README.md). Each **subdirectory** of `themes/` is one theme. The folder name is the theme id used by the CLI (`export`, `validate`, etc.).

## Theme layout

Each theme directory has three files:

| File | Role |
| ---- | ---- |
| `theme.yaml` | Metadata (display name, description, author, variants, tags) |
| `colorsystem.yaml` | Palette definitions (primary/secondary/syntax/group, etc.) |
| `mappings.yaml` | Semantic UI and syntax slot references; optional `css_overrides` for Spyder help CSS |

## Catalog

| Theme | Description |
| ----- | ----------- |
| **Ayu** (`ayu`) | Official Ayu Dark and Light palettes adapted for Spyder |
| **Brutalism** (`brutalism`) | Brutalism palette inspired in the brutalist architecture |
| **Catppuccin Mocha** (`catppuccin-mocha`) | A personal version of the Catppuccin theme, Mocha variant |
| **Dracula** (`dracula`) | Based on the Dracula color palette by Zeno Rocha |
| **GitHub Dark** (`github-dark`) | GitHub's modern Dark Default palette adapted for Spyder |
| **GitHub Dark Dimmed** (`github-dark-dimmed`) | GitHub's softer Dark Dimmed palette adapted for Spyder |
| **Gruvbox** (`gruvbox`) | A personal version of the classic Gruvbox theme |
| **IDLE** (`idle`) | A personal version of the default theme from the famous Idle editor |
| **Inkpot** (`inkpot`) | A port of the Vim InkPot theme |
| **Material** (`material`) | Sublime Text Material Theme: default/Oceanic dark and Lighter |
| **Miami Nights** (`miami-nights`) | Synthwave / Miami Nights palette from JupyterLab Miami Nights (timkpaine) |
| **Monokai** (`monokai`) | Sublime Text's Adaptive/Monokai dark combination, with a custom Spyder light variant |
| **Notepad++** (`notepad++`) | A personal version of the default theme from the Notepad++ editor, originally from Eclipse |
| **Obsidian** (`obsidian`) | A personal version of the Obsidian theme from Eclipse |
| **One Dark Pro** (`one-dark-pro`) | One Dark Pro's original dark palette and Python syntax colors |
| **Solarized** (`solarized`) | Based on the Solarized color palette by Ethan Schoonover, enhanced with a wider range of colors |
| **Spyder** (`spyder`) | The original Spyder theme, based on the default QDarkStyleSheet color palette |
| **Sublime Mariana** (`sublime-mariana`) | Sublime Text 4's Adaptive/Mariana combination with dark chrome and native editor colors |
| **Tokyo Night** (`tokyonight`) | Tokyo Night Night and Day palettes from folke/tokyonight.nvim |
| **Tokyo Night AltSynt** (`tokyo-night-altsynt`) | Avetis's VS Code Tokyo Night AltSynt palette, with Python variable and nested bracket colors |
| **VS Code 2017** (`vscode-2017`) | Microsoft's classic Dark+ and Light+ palettes from VS Code 1.19.1 (2017) |
| **VS Code 2026** (`vscode-2026`) | Microsoft's official Dark 2026 and Light 2026 palettes, including their new syntax colors |
| **Zenburn** (`zenburn`) | A low-contrast color scheme easy for your eyes and designed to keep you in the zone for long programming sessions |

The ports use the upstream palettes from [Ayu](https://github.com/ayu-theme/ayu-colors), [GitHub's VS Code themes](https://github.com/primer/github-vscode-theme), [One Dark Pro](https://github.com/Binaryify/OneDark-Pro), [Sublime Text Material Theme](https://github.com/SublimeText/material-theme), [Tokyo Night](https://github.com/folke/tokyonight.nvim), [Tokyo Night AltSynt](https://github.com/AvetisDN/tokyo-dark-theme), [VS Code 1.19.1](https://github.com/microsoft/vscode/tree/0759f77bb8d86658bc935a10a64f6182c5a1eeba/extensions/theme-defaults/themes), and [VS Code's 2026 themes](https://github.com/microsoft/vscode/tree/main/extensions/theme-defaults/themes). Pinned source revisions and adaptation notes are in each theme's YAML comments; upstream license notices are in each theme's `LICENSE`. These ports use MIT except the folke Tokyo Night port, which uses Apache-2.0.

Ayu, Material, Tokyo Night, VS Code 2017 and VS Code 2026 include dark and light variants. GitHub Dark, GitHub Dark Dimmed and One Dark Pro include only a dark variant. GitHub Dark uses the modern **Dark Default** palette. VS Code 2017 uses **Dark+ / Light+** from the December 2017 release.

Sublime Mariana is dark-only. Its dark variant and Monokai's dark variant pair the respective editor scheme with **Adaptive** ([official explanation](https://www.sublimetext.com/blog/articles/the-adaptive-theme)). Both use the bundled resources in [Sublime Text 4 build 4215](https://www.sublimetext.com/download) (25 September 2026), including colors for selection, hover, brackets, feedback and help views that are not visible in the reference screenshots. Monokai's light variant remains a custom Spyder adaptation; Sublime's bundled Monokai scheme has no light variant.

The screenshot references use Adaptive's `file_medium_dark` appearance: dark sidebar and tab strip, editor-colored active tabs, neutral row selections, and a darker status bar. The palette maps the sidebar independently of the editor; it does not use a saturated blue or pink fill for selected tabs. Native HSL colors are converted to sRGB hex values rather than sampled from color-managed screenshots. Qt bracket fills, variable explorer groups, and Help/Appeal/Pydoc styles are adaptations. Native syntax/selection colors and UI brightness ordering retain advisories under ThemeWeaver's stricter contrast rules.

The companion `spyder6_ok97465` fork supports 20 optional Python roles, including separate word/symbol operators, class names and references, calls, docstrings, types, parameters, variables and six bracket depths. Fifteen UI roles separate gutter, toolbar, status, tab and tree colors, including inactive selection text. Native tab accents can select the inner/outer edge and stroke width. These roles are explicit in **all 23 themes / 41 supported variants**, including the 12 original themes / 24 variants. External themes that omit them retain their existing behavior. Stock Spyder can load the palettes through its shared syntax slots. Contextual Python refinements use tokens and a cached AST; syntactically incomplete code falls back for AST-dependent colors, and files exceeding 3,000 blocks or 200,000 characters retain block highlighting.

The original Brutalism, Catppuccin Mocha, Dracula, Gruvbox, IDLE, Inkpot, Miami Nights, Notepad++, Obsidian, Solarized, Spyder and Zenburn entries retain their established Spyder adaptations and custom counterparts. Their new roles distinguish source-supported syntax without replacing personal palettes wholesale. Qt toolbar/status/tree shades remain based on each existing color system; selected tab and row text is chosen independently for readability in both variants. No rainbow bracket colors are introduced for schemes that use a single punctuation color. Source references and adaptation boundaries are documented in each mapping file and the audit report.

The bundled Sublime Text resources specify no open-source license; source attribution and checksums are recorded in [`sublime-mariana/LICENSE`](sublime-mariana/LICENSE) and [`monokai/LICENSE`](monokai/LICENSE). The MIT statement above applies to the linked GitHub ports, not to these bundled Sublime Text references.

Tokyo Night AltSynt is a separate dark-only port of Avetis's VS Code extension 1.0.2, pinned to commit `d075816a68955bffcb4dae9cf26a44538b7619a1`. It preserves its navy editor, distinct sidebar/tab/panel backgrounds, green definitions and builtins, red operators, yellow strings/docstrings and purple numbers. Its native three-color bracket cycle repeats across six explicit depth slots. Python's generic unresolved calls use the native editor foreground. Class references are identified from declarations and base-class context; this is a local syntax adaptation, without Pylance's external symbol/type resolution. The original folke-based `tokyonight` Night/Day theme remains a separate catalog entry.

Each port includes editor syntax, interface and variable explorer colors, and Help/Appeal/Pydoc CSS mappings. Intermediate widget shades and group fills are adapted for Qt. Material Lighter retains documented text-color adjustments for readability. Native low-contrast colors and UI brightness ordering can trigger ThemeWeaver contrast advisories. The source audit, scope-specific corrections, remaining limits and verification commands are documented in [THEME_AUDIT_KO.md](THEME_AUDIT_KO.md).

## Working with ThemeWeaver

Run all `pixi` / CLI commands from the **ThemeWeaver repository root** (the directory that contains `pyproject.toml` and this `themes/` folder). The tools resolve `themes/` relative to the current working directory unless you pass `--theme-dir`.

### Setup

- Install [Pixi](https://pixi.sh/) and run `pixi install` in the repo root.
- Python and dependencies are provided by the Pixi environment (see the main [README](../README.md#project-setup)).

### Use this standalone source checkout

This repository contains YAML sources and cannot itself be installed with `pip install -e .`. In a separate [ThemeWeaver checkout](https://github.com/spyder-ide/spyder-themeweaver), export this directory directly:

```bash
# Run from the ThemeWeaver repository root, after pixi install.
pixi run cli export --all --theme-dir /path/to/spyder-themes_ok97465
pixi run package

# Run with the Python environment that launches Spyder activated.
python -m pip install -U -e /path/to/spyder-themeweaver/dist/spyder_themes
```

Before packaging for Spyder 6.2.0a3, check `[tool.themeweaver.spyder-package].version` in ThemeWeaver's `pyproject.toml`: Spyder requires `spyder-themes>=1.0.16,<1.1.0`, so an older checkout still set to `1.0.15` needs that bundle version updated. Keep the full exported bundle, including the default `spyder` theme. Restart Spyder after installation and select the new theme in **Preferences > Appearance**. YAML edits require another export and package step even with an editable installation.

### Create a new theme (`generate`)

`generate` writes `theme.yaml`, `colorsystem.yaml`, and `mappings.yaml` under `themes/<name>/`. It does **not** write to `build/`; use `export` after you are satisfied.

You need **six seed colors** in order: primary, secondary, error, success, warning, group (see the table in [Theme generation](../README.md#theme-generation) in the main README). Each color must be `#RRGGBB` (six hex digits; shorthand `#RGB` is not accepted).

Minimal example:

```bash
pixi run generate my_theme \
  --colors "#1e1e2e" "#b4befe" "#f38ba8" "#a6e3a1" "#fab387" "#eba0ac" \
  --display-name "My Custom Theme"
```

Other inputs:

- **YAML definition:** `pixi run generate my_theme --from-yaml theme-definition.yaml` (see [From a YAML definition file](../README.md#from-a-yaml-definition-file)).
- **Syntax seeds or full 17-color syntax lists, editor bold/italic:** `--syntax-colors-dark`, `--syntax-colors-light`, `--syntax-format`, or the equivalent fields in the YAML definition.

Useful flags: `--overwrite`, `--output-dir <path>` (if not `./themes`, pass `--theme-dir` to `export` / `validate`), `--variants dark light`, `--no-validate-contrast`.

Full detail: [Theme generation](../README.md#theme-generation), [Syntax colors](../README.md#syntax-colors), [Syntax format](../README.md#syntax-format).

### Validate and export

```bash
pixi run validate my_theme
pixi run validate-contrast my_theme
pixi run export my_theme          # all enabled variants into build/
pixi run export-dark my_theme     # dark only
pixi run export-light my_theme    # light only
```

`validate` checks YAML structure; `validate-contrast` checks colors against bundled Spyder UI rules. Export uses QDarkStyle and writes assets under `build/`, including Spyder help `default.css` per variant. Themes may override help CSS color mappings via optional `css_overrides` in `mappings.yaml` (see [Help CSS overrides](../README.md#help-css-overrides)).

For the new themes in this standalone checkout:

```bash
pixi run cli export --theme github-dark github-dark-dimmed one-dark-pro vscode-2017 \
  --theme-dir /path/to/spyder-themes_ok97465

# Sublime Text's Adaptive/Mariana and Adaptive/Monokai combinations.
pixi run cli export --theme sublime-mariana monokai \
  --theme-dir /path/to/spyder-themes_ok97465

# For dark-only themes, select the supported variant explicitly for contrast checks.
pixi run validate-contrast github-dark --variant dark \
  --theme-dir /path/to/spyder-themes_ok97465
```

**Shell quoting:** If the theme id contains characters the shell treats specially (e.g. `notepad++`), quote it:

```bash
pixi run export 'notepad++'
```

### Edit an existing theme

You may hand-edit `colorsystem.yaml`, `mappings.yaml`, and `theme.yaml` after generation or as a fully manual theme. A heavily commented reference for syntax slot layout is `catppuccin-mocha/colorsystem.yaml` (`CatppuccinMochaSyntaxDark` / `CatppuccinMochaSyntaxLight`).

Optional `css_overrides` in `mappings.yaml` replace built-in help CSS color map entries. Omit the section to keep defaults (the `spyder` theme has none). Example:

```yaml
css_overrides:
  --hover-color: COLOR_ACCENT_2
  --border-color:
    dark: Primary.B60
    light: Primary.B100
```

After edits, run `validate` / `validate-contrast` and `export` again.

### List themes and metadata

```bash
pixi run list-themes
pixi run theme-info solarized
```

The underlying CLI subcommand for listing is `list` (`pixi run cli list`).

### Preview, sync, and packaging

- **Preview** (Qt): export first, then `pixi run preview` from the repo root (see [Quick start](../README.md#quick-start)).
- **Dev sync:** `pixi run dev-sync <name>` exports and copies into an editable `spyder_themes` tree for a fast edit loop (see [Dev sync](../README.md#dev-sync)).
- **Local deploy:** `pixi run deploy-local <name>` exports that theme, then packages everything already under `build/` and installs editable (see [Local deploy](../README.md#local-deploy)).
- **Spyder wheel/sdist:** `export` or `export-all`, then `pixi run package` (see [Spyder Python package](../README.md#spyder-python-package-python-package)).

### Color helpers (optional)

Palette, gradient, and interpolation commands are documented under [Color utilities](../README.md#color-utilities). They print to stdout and do not modify `themes/` unless you copy values yourself.
