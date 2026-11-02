#!/usr/bin/env python3
"""Check source/export parity and coverage of the companion Spyder's roles.

Run with ThemeWeaver's Python environment. This checks the actual generated
palette, not only whether names occur in YAML. Native source matching is
documented in each port's palette comments and THEME_AUDIT_KO.md.
"""

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

import yaml

from themeweaver.color_utils import contrast_ratio
from themeweaver.core.palette import create_palettes
from themeweaver.core.syntax_schema import formatted_editor_keys


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"Duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def read_yaml(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)


def runtime_roles(spyder_dir):
    manager = ast.parse((spyder_dir / "spyder/utils/theme_manager.py").read_text())
    syntax = None
    for node in manager.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id == "OPTIONAL_PYTHON_SCHEME_KEYS"
            for target in node.targets
        ):
            syntax = {"EDITOR_" + name.upper() for name in ast.literal_eval(node.value)}
    if syntax is None:
        raise ValueError("Companion Spyder optional syntax schema was not found")

    stylesheet = ast.parse((spyder_dir / "spyder/utils/stylesheet.py").read_text())
    ui = set()
    for node in stylesheet.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_apply_optional_"):
            ui.update(
                item.value for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                and item.value.startswith("COLOR_")
            )
    for relative in ("spyder/utils/stylesheet.py", "spyder/plugins/editor/panels/linenumber.py"):
        for node in ast.walk(ast.parse((spyder_dir / relative).read_text())):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "getattr" and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "SpyderPalette"
                    and isinstance(node.args[1], ast.Constant)):
                name = node.args[1].value
                if isinstance(name, str) and name.startswith("COLOR_"):
                    ui.add(name)
    return syntax, ui


def load_generated(folder, name):
    unique_name = "verified_port_" + name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(
        unique_name, folder / "__init__.py", submodule_search_locations=[str(folder)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module


def optional_contrast(palette, syntax_roles):
    """Report optional foreground/background pairs; native colors are advisory.

    These simple 4.5:1 text / 3:1 gutter comparisons supplement ThemeWeaver's
    legacy 71 rules. They do not claim accessibility certification or change
    an upstream scheme to make an advisory pass.
    """
    pairs = [(role, "EDITOR_BACKGROUND", 4.5) for role in sorted(syntax_roles)]
    pairs += [
        ("COLOR_EDITOR_LINE_NUMBER", "EDITOR_SIDEAREAS", 3.0),
        ("COLOR_STATUSBAR_TEXT", "COLOR_STATUSBAR_BACKGROUND", 4.5),
        ("COLOR_TAB_TEXT", "COLOR_BACKGROUND_4", 4.5),
        ("COLOR_TAB_TEXT", "COLOR_TAB_HOVER_BACKGROUND", 4.5),
        ("COLOR_TAB_SELECTED_TEXT", "COLOR_TAB_SELECTED_BACKGROUND", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_BACKGROUND_1", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_TREE_HOVER_BACKGROUND", 4.5),
        ("COLOR_TREE_SELECTED_TEXT", "COLOR_TREE_SELECTED_BACKGROUND", 4.5),
        ("COLOR_TREE_INACTIVE_SELECTION_TEXT",
         "COLOR_TREE_INACTIVE_SELECTION_BACKGROUND", 4.5),
    ]
    results = []
    for foreground, background, minimum in pairs:
        fg, bg = getattr(palette, foreground), getattr(palette, background)
        fg = fg[0] if isinstance(fg, tuple) else fg
        ratio = contrast_ratio(fg, bg)
        results.append({"foreground": foreground, "background": background,
                        "ratio": round(ratio, 3), "minimum": minimum,
                        "passed": ratio >= minimum})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--theme-dir", type=Path, default=root)
    parser.add_argument("--spyder-dir", type=Path, default=root.parent / "spyder6_ok97465")
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--themes", nargs="+")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    syntax_roles, ui_roles = runtime_roles(args.spyder_dir)
    names = args.themes or sorted(
        path.name for path in args.theme_dir.iterdir()
        if (path / "theme.yaml").is_file()
    )
    if not names:
        parser.error("No theme metadata found")
    hex_color = re.compile(r"#[0-9A-Fa-f]{6}\Z")
    results = []
    errors = []
    for name in names:
        try:
            folder = args.theme_dir / name
            metadata = read_yaml(folder / "theme.yaml")
            colors = read_yaml(folder / "colorsystem.yaml")
            mappings = read_yaml(folder / "mappings.yaml")
            assert metadata["name"] == name, "Metadata/folder id mismatch"
            variants = {key for key, enabled in metadata["variants"].items() if enabled}
            assert variants == set(mappings["semantic_mappings"]), "Variant mismatch"
            for palette in colors.values():
                assert all(hex_color.fullmatch(value) for value in palette.values()), "Invalid hex color"
            aliases = mappings["color_classes"]
            for alias, source in aliases.items():
                assert source in colors, f"Unknown color class {alias}: {source}"
            palettes = create_palettes(name, themes_dir=args.theme_dir)
            exported_dir = args.build_dir / name
            exported = load_generated(exported_dir, name)
            assert exported.THEME_ID == name
            assert read_yaml(exported_dir / "theme.yaml") == metadata, "Stale exported metadata"
            assert (exported_dir / "theme.yaml").read_bytes() == (folder / "theme.yaml").read_bytes(), "Stale exported source notice"
            # Legacy themes have license metadata but no separate source notice.
            # Preserve every notice that exists without fabricating new ones.
            if (folder / "LICENSE").is_file():
                assert (exported_dir / "LICENSE").read_bytes() == (folder / "LICENSE").read_bytes(), "Stale/missing notice"
            for variant in sorted(variants):
                semantic = mappings["semantic_mappings"][variant]
                missing = syntax_roles.union(ui_roles) - semantic.keys()
                assert not missing, f"{variant}: missing roles {sorted(missing)}"
                source_palette = palettes.get_palette(variant)
                generated_palette = getattr(exported, "SpyderPalette" + variant.title())
                for key, reference in semantic.items():
                    ref = reference[0] if isinstance(reference, list) else reference
                    if isinstance(ref, str):
                        alias, slot = ref.split(".")
                        assert slot in colors[aliases[alias]], f"Unresolved {key}: {ref}"
                    actual = getattr(generated_palette, key)
                    assert actual == getattr(source_palette, key), f"{variant}: stale export {key}"
                    if key in syntax_roles.union(formatted_editor_keys()):
                        assert (isinstance(actual, tuple) and len(actual) == 3
                                and hex_color.fullmatch(actual[0])
                                and type(actual[1]) is bool and type(actual[2]) is bool), key
                    elif key in ui_roles:
                        assert isinstance(actual, str) and hex_color.fullmatch(actual), key
                for asset in (f"{variant}style.qss", "default.css", "appeal.css", "pydoc.css"):
                    asset_path = exported_dir / variant / asset
                    assert asset_path.is_file(), f"Missing {variant}/{asset}"
                    aliases_pattern = "|".join(re.escape(alias) for alias in aliases)
                    assert not re.search(rf"\b(?:{aliases_pattern})\.B\d+\b", asset_path.read_text()), f"Unresolved color in {asset}"
                results.append({"theme": name, "variant": variant,
                                "syntax_roles": len(syntax_roles), "ui_roles": len(ui_roles),
                                "background": generated_palette.EDITOR_BACKGROUND,
                                "foreground": generated_palette.EDITOR_NORMAL[0],
                                "optional_contrast_advisories": optional_contrast(
                                    generated_palette, syntax_roles)})
                print(f"PASS {name}/{variant}: {len(syntax_roles)} syntax + {len(ui_roles)} UI roles; source/export parity")
        except (AssertionError, KeyError, ValueError, OSError, ImportError) as error:
            errors.append({"theme": name, "error": str(error)})
            print(f"FAIL {name}: {error}", file=sys.stderr)
    report = {"themes": len(names), "variants_verified": len(results),
              "results": results, "errors": errors}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified {len(results)} variants in {len(names)} themes; {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
