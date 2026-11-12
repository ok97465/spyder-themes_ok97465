#!/usr/bin/env python3
"""Check source/export parity and coverage of the companion Spyder's roles.

Run .tools/verify_port_mappings.py with ThemeWeaver's Python environment.
This checks the actual generated palette, not only whether names occur in
YAML. Native source matching is documented in each port's palette comments
and THEME_AUDIT_KO.md.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import yaml

from themeweaver.color_utils import contrast_ratio
from themeweaver.core.palette import create_palettes
from themeweaver.core.syntax_schema import formatted_editor_keys


STATE_COLOR_ROLES = {
    "COLOR_TAB_BACKGROUND", "COLOR_BUTTON_BACKGROUND", "COLOR_BUTTON_TEXT",
    "COLOR_BUTTON_HOVER_BACKGROUND", "COLOR_BUTTON_PRESSED_BACKGROUND",
    "COLOR_BUTTON_BORDER",
}
POPUP_COLOR_ROLES = {
    "COLOR_MENU_BACKGROUND", "COLOR_MENU_TEXT",
    "COLOR_MENU_SELECTED_BACKGROUND", "COLOR_MENU_SELECTED_TEXT",
    "COLOR_MENU_BORDER", "COLOR_SWITCHER_BACKGROUND",
    "COLOR_SWITCHER_SELECTED_BACKGROUND", "COLOR_SWITCHER_BORDER",
    "COLOR_SWITCHER_INPUT_BACKGROUND",
}
OPTIONAL_POPUP_COLOR_ROLES = {
    "COLOR_MENU_SELECTED_BORDER", "COLOR_SWITCHER_SELECTED_BORDER",
}
MIN_SURFACE_CONTRAST = 1.15
MIN_PANE_BORDER_CONTRAST = 1.4
UI_STATE_POLICIES = {"distinct-fills", "contrast-borders"}
# A high-contrast UI may use the same fill for every surface. Its visible
# boundaries, rather than incidental RGB differences, must remain strong.
BORDER_STATE_PAIRS = (
    ("COLOR_PANE_BORDER", "COLOR_BACKGROUND_1"),
    # The companion Help frame uses this legacy role for its inactive edge.
    ("COLOR_BACKGROUND_4", "COLOR_BACKGROUND_1"),
    ("COLOR_EDITOR_BORDER", "EDITOR_BACKGROUND"),
    ("COLOR_SIDEBAR_BORDER", "COLOR_BACKGROUND_1"),
    ("COLOR_BUTTON_BORDER", "COLOR_BACKGROUND_1"),
    ("COLOR_ACCENT_3", "COLOR_BACKGROUND_1"),
    ("COLOR_ACCENT_3", "EDITOR_BACKGROUND"),
    ("COLOR_TAB_SELECTED_ACCENT", "COLOR_TAB_SELECTED_BACKGROUND"),
)
BORDER_STATE_ROLES = {role for pair in BORDER_STATE_PAIRS for role in pair}
MIN_STATE_BORDER_CONTRAST = 3.0


def has_popup_colors(palette):
    """Keep legacy palettes valid; an opted-in popup bundle must be complete."""
    present = {role for role in POPUP_COLOR_ROLES if hasattr(palette, role)}
    if present and present != POPUP_COLOR_ROLES:
        raise ValueError(f"Incomplete popup color bundle: {sorted(POPUP_COLOR_ROLES - present)}")
    return bool(present)


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
        ("COLOR_TAB_TEXT", "COLOR_TAB_BACKGROUND", 4.5),
        ("COLOR_TAB_TEXT", "COLOR_TAB_HOVER_BACKGROUND", 4.5),
        ("COLOR_TAB_SELECTED_TEXT", "COLOR_TAB_SELECTED_BACKGROUND", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_BACKGROUND_1", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_TREE_HOVER_BACKGROUND", 4.5),
        ("COLOR_TREE_SELECTED_TEXT", "COLOR_TREE_SELECTED_BACKGROUND", 4.5),
        ("COLOR_TREE_INACTIVE_SELECTION_TEXT",
         "COLOR_TREE_INACTIVE_SELECTION_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_HOVER_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_PRESSED_BACKGROUND", 4.5),
        ("EDITOR_NORMAL", "EDITOR_CURRENTLINE", 4.5),
    ]
    if hasattr(palette, "EDITOR_DEBUGLINE"):
        pairs.append(("EDITOR_NORMAL", "EDITOR_DEBUGLINE", 4.5))
    results = []
    for foreground, background, minimum in pairs:
        fg, bg = getattr(palette, foreground), getattr(palette, background)
        fg = fg[0] if isinstance(fg, tuple) else fg
        ratio = contrast_ratio(fg, bg)
        results.append({"foreground": foreground, "background": background,
                        "ratio": round(ratio, 3), "minimum": minimum,
                        "passed": ratio >= minimum})
    return results


def ui_contrast(palette):
    """Check ordinary UI text and primary toolbar icons, excluding disabled UI."""
    pairs = [
        ("COLOR_TAB_TEXT", "COLOR_TAB_BACKGROUND", 4.5),
        ("COLOR_TAB_TEXT", "COLOR_TAB_HOVER_BACKGROUND", 4.5),
        ("COLOR_TAB_SELECTED_TEXT", "COLOR_TAB_SELECTED_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_HOVER_BACKGROUND", 4.5),
        ("COLOR_BUTTON_TEXT", "COLOR_BUTTON_PRESSED_BACKGROUND", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_BACKGROUND_1", 4.5),
        ("COLOR_TREE_TEXT", "COLOR_TREE_HOVER_BACKGROUND", 4.5),
        ("COLOR_TREE_SELECTED_TEXT", "COLOR_TREE_SELECTED_BACKGROUND", 4.5),
        ("COLOR_TREE_INACTIVE_SELECTION_TEXT",
         "COLOR_TREE_INACTIVE_SELECTION_BACKGROUND", 4.5),
        ("COLOR_STATUSBAR_TEXT", "COLOR_STATUSBAR_BACKGROUND", 4.5),
        ("COLOR_TEXT_1", "COLOR_TOOLBAR_BACKGROUND", 4.5),
        ("ICON_1", "COLOR_TOOLBAR_BACKGROUND", 3.0),
    ]
    if has_popup_colors(palette):
        pairs.extend([
            ("COLOR_MENU_TEXT", "COLOR_MENU_BACKGROUND", 4.5),
            ("COLOR_MENU_SELECTED_TEXT", "COLOR_MENU_SELECTED_BACKGROUND", 4.5),
            # The real Switcher embeds COLOR_TEXT_1 in its row HTML, including
            # selected rows; a Qt highlighted-text color cannot replace it.
            ("COLOR_TEXT_1", "COLOR_SWITCHER_BACKGROUND", 4.5),
            ("COLOR_TEXT_1", "COLOR_SWITCHER_SELECTED_BACKGROUND", 4.5),
            ("COLOR_TEXT_1", "COLOR_SWITCHER_INPUT_BACKGROUND", 4.5),
        ])
    checks = []
    for foreground, background, minimum in pairs:
        fg, bg = getattr(palette, foreground), getattr(palette, background)
        ratio = contrast_ratio(fg, bg)
        checks.append({"foreground": foreground, "background": background,
                       "foreground_color": fg, "background_color": bg,
                       "ratio": round(ratio, 3), "minimum": minimum,
                       "passed": ratio >= minimum})
    return checks


def state_distinctions(palette, policy="distinct-fills", pane_policy="visible"):
    """Check the declared way a theme distinguishes its controls and states."""
    if policy not in UI_STATE_POLICIES:
        raise ValueError(f"Invalid ui_state_policy: {policy!r}")
    if pane_policy not in ("visible", "borderless"):
        raise ValueError(f"Invalid pane_border_policy: {pane_policy!r}")
    pairs = [
        ("COLOR_TOOLBAR_BACKGROUND", "COLOR_BACKGROUND_1"),
        ("COLOR_TOOLBAR_BACKGROUND", "EDITOR_BACKGROUND"),
        ("COLOR_TAB_BACKGROUND", "COLOR_BACKGROUND_1"),
        ("COLOR_TAB_BACKGROUND", "EDITOR_BACKGROUND"),
        ("COLOR_BUTTON_BACKGROUND", "COLOR_BACKGROUND_1"),
        ("COLOR_BUTTON_BACKGROUND", "EDITOR_BACKGROUND"),
        ("COLOR_BUTTON_HOVER_BACKGROUND", "COLOR_BUTTON_BACKGROUND"),
        ("COLOR_BUTTON_PRESSED_BACKGROUND", "COLOR_BUTTON_BACKGROUND"),
        ("EDITOR_CURRENTLINE", "EDITOR_BACKGROUND"),
    ]
    if hasattr(palette, "EDITOR_DEBUGLINE"):
        pairs.extend([
            ("EDITOR_DEBUGLINE", "EDITOR_BACKGROUND"),
            ("EDITOR_DEBUGLINE", "EDITOR_CURRENTLINE"),
        ])
    results = []
    for first, second in pairs:
        a, b = getattr(palette, first), getattr(palette, second)
        if policy == "distinct-fills":
            assert a.lower() != b.lower(), f"Identical state fills: {first} and {second}"
        ratio = contrast_ratio(a, b)
        results.append({"first": first, "second": second, "kind": "fill",
                        "first_color": a, "second_color": b,
                        "contrast": round(ratio, 3),
                        "minimum_visibility_advisory": MIN_SURFACE_CONTRAST,
                        "visibility_advisory_passed": ratio >= MIN_SURFACE_CONTRAST})
    boundaries = [
        ("COLOR_ACCENT_3", "COLOR_BACKGROUND_1", True),
        ("COLOR_ACCENT_3", "EDITOR_BACKGROUND", True),
        ("COLOR_PANE_BORDER", "COLOR_BACKGROUND_1", False),
        ("COLOR_EDITOR_BORDER", "EDITOR_BACKGROUND", False),
        ("COLOR_SIDEBAR_BORDER", "COLOR_BACKGROUND_1", False),
        ("COLOR_BACKGROUND_4", "COLOR_BACKGROUND_1", False),
    ]
    for first, second, focused in boundaries:
        resolved = first if hasattr(palette, first) else "COLOR_BACKGROUND_4"
        a, b = getattr(palette, resolved), getattr(palette, second)
        ratio = contrast_ratio(a, b)
        enforced = focused or pane_policy == "visible"
        assert not enforced or ratio >= MIN_PANE_BORDER_CONTRAST, (
            f"Insufficient {'active' if focused else 'inactive'} pane boundary: "
            f"{first}/{second} {ratio:.3f}:1 < {MIN_PANE_BORDER_CONTRAST}:1"
        )
        results.append({
            "first": first, "first_resolved_role": resolved, "second": second,
            "kind": "focused-border" if focused else "inactive-border",
            "first_color": a, "second_color": b, "contrast": round(ratio, 3),
            "minimum": MIN_PANE_BORDER_CONTRAST,
            "visibility_enforced": enforced,
            "passed": not enforced or ratio >= MIN_PANE_BORDER_CONTRAST,
        })
    if policy == "contrast-borders":
        boundary_pairs = list(BORDER_STATE_PAIRS)
        if hasattr(palette, "COLOR_SWITCHER_SELECTED_BACKGROUND"):
            indicator = (
                "COLOR_SWITCHER_SELECTED_BORDER"
                if hasattr(palette, "COLOR_SWITCHER_SELECTED_BORDER")
                else "COLOR_SWITCHER_SELECTED_BACKGROUND"
            )
            boundary_pairs.extend((indicator, background) for background in (
                "COLOR_SWITCHER_BACKGROUND", "COLOR_SWITCHER_SELECTED_BACKGROUND",
            ) if indicator != background)
        for first, second in boundary_pairs:
            a, b = getattr(palette, first), getattr(palette, second)
            ratio = contrast_ratio(a, b)
            assert ratio >= MIN_STATE_BORDER_CONTRAST, (
                f"Insufficient state boundary: {first}/{second} "
                f"{ratio:.3f}:1 < {MIN_STATE_BORDER_CONTRAST}:1"
            )
            results.append({"first": first, "second": second, "kind": "border",
                            "first_color": a, "second_color": b,
                            "contrast": round(ratio, 3),
                            "minimum": MIN_STATE_BORDER_CONTRAST, "passed": True})
    return results


def vscode_fox_source_checks(name, variant, palette, folder, extension_dir):
    """Compare the two VS Code ports with an explicitly supplied source install.

    This independent check complements YAML/export parity: changing both a
    palette and its mapping cannot silently change the native source colors.
    Qt-only adaptations (shared inactive tab/Help frame, hover text, button
    pressed state and active frame) remain covered by the ordinary UI checks.
    """
    if extension_dir is None or name not in {"nightfox", "nordfox"}:
        return None
    assert variant == "dark", f"Unexpected VS Code Fox variant: {variant}"
    source_path = extension_dir / "themes" / f"{name}.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    notices = "\n".join(
        (folder / filename).read_text(encoding="utf-8")
        for filename in ("theme.yaml", "colorsystem.yaml", "mappings.yaml")
    )
    assert source_hash in notices, f"Unrecorded {name} source SHA-256: {source_hash}"
    package = json.loads((extension_dir / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "nightfox-theme-collections", "Unexpected VS Code source extension"
    colors = source["colors"]
    semantic = source["semanticTokenColors"]
    checks = []

    def check(role, expected, origin, formatting=None, source_color=None):
        actual = getattr(palette, role)
        color = actual[0] if isinstance(actual, tuple) else actual
        assert color.lower() == expected.lower(), (
            f"VS Code source mismatch {role}: {color} != {expected} ({origin})"
        )
        if formatting is not None:
            assert tuple(actual[1:]) == formatting, (
                f"VS Code source style mismatch {role}: {actual[1:]} != {formatting}"
            )
        checks.append({"role": role, "source_role": origin, "color": expected,
                       "source_color": source_color or expected,
                       "formatting": formatting, "passed": True})

    native_ui = {
        "EDITOR_BACKGROUND": "editor.background",
        "EDITOR_SIDEAREAS": "editorGutter.background",
        "EDITOR_CURRENTLINE": "editor.lineHighlightBackground",
        "EDITOR_OCCURRENCE": "editor.wordHighlightBackground",
        "EDITOR_MATCHED_P": "editorBracketMatch.background",
        "COLOR_EDITOR_LINE_NUMBER": "editorLineNumber.foreground",
        "COLOR_STATUSBAR_BACKGROUND": "statusBar.background",
        "COLOR_STATUSBAR_TEXT": "statusBar.foreground",
        "COLOR_TOOLBAR_BACKGROUND": "titleBar.activeBackground",
        "COLOR_TAB_SELECTED_BACKGROUND": "tab.activeBackground",
        "COLOR_TAB_SELECTED_TEXT": "tab.activeForeground",
        "COLOR_TAB_SELECTED_ACCENT": "tab.activeBorderTop",
        "COLOR_PANE_BORDER": "panel.border",
        "COLOR_EDITOR_BORDER": "editorGroup.border",
        "COLOR_SIDEBAR_BORDER": "sideBar.border",
        "COLOR_BUTTON_BACKGROUND": "button.background",
        "COLOR_BUTTON_TEXT": "button.foreground",
        "COLOR_BUTTON_HOVER_BACKGROUND": "button.hoverBackground",
        "COLOR_MENU_BACKGROUND": "menu.background",
        "COLOR_MENU_TEXT": "menu.foreground",
        "COLOR_MENU_SELECTED_BACKGROUND": "menu.selectionBackground",
        "COLOR_MENU_SELECTED_TEXT": "menu.selectionForeground",
        "COLOR_MENU_BORDER": "menu.border",
        # The source leaves quickInput.* unset; VS Code inherits these roles.
        "COLOR_SWITCHER_BACKGROUND": "editorWidget.background",
        "COLOR_SWITCHER_SELECTED_BACKGROUND": "list.activeSelectionBackground",
        "COLOR_SWITCHER_BORDER": "editorWidget.border",
        "COLOR_SWITCHER_INPUT_BACKGROUND": "input.background",
        "COLOR_TREE_HOVER_BACKGROUND": "list.hoverBackground",
        "COLOR_TREE_SELECTED_BACKGROUND": "list.activeSelectionBackground",
        "COLOR_TREE_SELECTED_TEXT": "list.activeSelectionForeground",
        "COLOR_TREE_INACTIVE_SELECTION_BACKGROUND": "list.inactiveSelectionBackground",
        "COLOR_TREE_INACTIVE_SELECTION_TEXT": "list.inactiveSelectionForeground",
    }
    for role, source_role in native_ui.items():
        native_color = colors[source_role]
        if name == "nordfox" and role in {
            "COLOR_MENU_SELECTED_BACKGROUND", "COLOR_SWITCHER_SELECTED_BACKGROUND",
            "COLOR_TREE_SELECTED_BACKGROUND",
        }:
            # Native #4F6074 with #CDCECF is only 4.09:1. The Spyder port
            # keeps the source text and darkens that selected surface slightly.
            check(role, "#48586B", f"Qt adaptation of colors.{source_role}",
                  source_color=native_color)
        else:
            check(role, native_color, f"colors.{source_role}")
    check("EDITOR_NORMAL", colors["editor.foreground"], "colors.editor.foreground", (False, False))
    native_syntax = {
        "EDITOR_KEYWORD": "keyword", "EDITOR_STORAGE": "keyword",
        "EDITOR_BUILTIN": "function.defaultLibrary",
        "EDITOR_DEFINITION": "function", "EDITOR_FUNCTION_CALL": "function",
        "EDITOR_STRING": "string", "EDITOR_DOCSTRING": "string", "EDITOR_NUMBER": "number",
        "EDITOR_INSTANCE": "variable.defaultLibrary",
        "EDITOR_OPERATOR": "operator", "EDITOR_WORD_OPERATOR": "operator",
        "EDITOR_CLASS": "class", "EDITOR_BASECLASS": "class",
        "EDITOR_CLASS_REFERENCE": "class", "EDITOR_TYPE": "type.defaultLibrary",
        "EDITOR_VARIABLE": "variable", "EDITOR_PARAMETER": "parameter",
        "EDITOR_CONSTANT": "variable.readonly", "EDITOR_MAGIC": "macro",
    }
    for role, source_role in native_syntax.items():
        check(role, semantic[source_role], f"semanticTokenColors.{source_role}")
    comments = next(item["settings"] for item in source["tokenColors"]
                    if item.get("name") == "Comment")
    styles = comments.get("fontStyle", "").split()
    check("EDITOR_COMMENT", comments["foreground"], "tokenColors.Comment",
          ("bold" in styles, "italic" in styles))
    brackets = next(item["settings"]["foreground"] for item in source["tokenColors"]
                    if item.get("name") == "Brackets")
    for role in ("EDITOR_PUNCTUATION", "EDITOR_SEPARATOR") + tuple(
        f"EDITOR_BRACKET_{depth}" for depth in range(1, 7)
    ):
        check(role, brackets, "tokenColors.Brackets")
    # The companion Spyder shares COLOR_ERROR_1 between the Stop icon and
    # Dependencies error-cell fill; COLOR_WARN_1 is a Dependencies warning fill.
    # Preserve native alert hues for ICON_4/5 while testing both actual uses of
    # the adapted shared roles. Nordfox's darker native toolbar permits 2.7:1
    # for this compromise, so it must not be reported as meeting 3:1.
    error_fill, warning_fill, stop_minimum = {
        "nightfox": ("#A5455F", "#6E6548", 3.0),
        "nordfox": ("#9D545D", "#736955", 2.7),
    }[name]
    check("COLOR_TREE_TEXT", colors["terminal.ansiBrightWhite"],
          "colors.terminal.ansiBrightWhite")
    check("ICON_4", colors["editorError.foreground"], "colors.editorError.foreground")
    check("ICON_5", colors["editorWarning.foreground"], "colors.editorWarning.foreground")
    check("COLOR_ERROR_1", error_fill,
          "Qt shared Dependencies/Stop adaptation of colors.editorError.foreground",
          source_color=colors["editorError.foreground"])
    check("COLOR_WARN_1", warning_fill,
          "Qt Dependencies adaptation of colors.editorWarning.foreground",
          source_color=colors["editorWarning.foreground"])
    shared_checks = []
    for foreground, background, minimum, usage in (
        ("COLOR_TREE_TEXT", "COLOR_ERROR_1", 4.5, "Dependencies error cell"),
        ("COLOR_TREE_TEXT", "COLOR_WARN_1", 4.5, "Dependencies warning cell"),
        ("COLOR_ERROR_1", "COLOR_TOOLBAR_BACKGROUND", stop_minimum,
         "Stop icon shared-role compromise"),
    ):
        fg, bg = getattr(palette, foreground), getattr(palette, background)
        ratio = contrast_ratio(fg, bg)
        assert ratio >= minimum, (
            f"{usage}: {foreground}/{background} {ratio:.3f}:1 < {minimum}:1"
        )
        shared_checks.append({
            "usage": usage, "foreground": foreground, "background": background,
            "foreground_color": fg, "background_color": bg,
            "ratio": round(ratio, 3), "minimum": minimum, "passed": True,
        })
    return {"extension": f"{package['publisher']}.{package['name']}",
            "version": package["version"], "path": str(source_path),
            "sha256": source_hash, "checks": checks,
            "shared_role_contrast_checks": shared_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--theme-dir", type=Path, default=root)
    parser.add_argument("--spyder-dir", type=Path, default=root.parent / "spyder6_ok97465")
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--themes", nargs="+")
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--vscode-extension-dir", type=Path,
        help="Also compare Nightfox/Nordfox against this Nightfox Theme Collections extension directory",
    )
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
            state_policy = metadata.get("ui_state_policy", "distinct-fills")
            assert state_policy in UI_STATE_POLICIES, f"Invalid ui_state_policy: {state_policy!r}"
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
                popup_present = POPUP_COLOR_ROLES.intersection(semantic)
                assert not popup_present or popup_present == POPUP_COLOR_ROLES, (
                    f"{variant}: incomplete popup color bundle: "
                    f"{sorted(POPUP_COLOR_ROLES - popup_present)}"
                )
                missing = syntax_roles.union(ui_roles, STATE_COLOR_ROLES) - semantic.keys()
                if state_policy == "contrast-borders":
                    missing.update(BORDER_STATE_ROLES - semantic.keys())
                assert not missing, f"{variant}: missing roles {sorted(missing)}"
                source_palette = palettes.get_palette(variant)
                generated_palette = getattr(exported, "SpyderPalette" + variant.title())
                native_source = vscode_fox_source_checks(
                    name, variant, generated_palette, folder, args.vscode_extension_dir
                )
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
                    elif key in ui_roles.union(STATE_COLOR_ROLES, POPUP_COLOR_ROLES,
                                              OPTIONAL_POPUP_COLOR_ROLES,
                                              {"EDITOR_DEBUGLINE"}):
                        assert isinstance(actual, str) and hex_color.fullmatch(actual), key
                for asset in (f"{variant}style.qss", "default.css", "appeal.css", "pydoc.css"):
                    asset_path = exported_dir / variant / asset
                    assert asset_path.is_file(), f"Missing {variant}/{asset}"
                    aliases_pattern = "|".join(re.escape(alias) for alias in aliases)
                    assert not re.search(rf"\b(?:{aliases_pattern})\.B\d+\b", asset_path.read_text()), f"Unresolved color in {asset}"
                ui_checks = ui_contrast(generated_palette)
                failed_ui = [check for check in ui_checks if not check["passed"]]
                if failed_ui:
                    detail = "; ".join(
                        f"{check['foreground']}/{check['background']} "
                        f"{check['ratio']}:1 < {check['minimum']}:1"
                        for check in failed_ui
                    )
                    error = f"{variant}: UI contrast: {detail}"
                    errors.append({"theme": name, "variant": variant,
                                   "error": error, "ui_contrast_checks": ui_checks})
                    print(f"FAIL {name}: {error}", file=sys.stderr)
                    continue
                results.append({"theme": name, "variant": variant,
                                "syntax_roles": len(syntax_roles), "ui_roles": len(ui_roles),
                                "background": generated_palette.EDITOR_BACKGROUND,
                                "foreground": generated_palette.EDITOR_NORMAL[0],
                                "ui_state_policy": state_policy,
                                "surface_visibility_basis": "1.15:1 fill distinction QA advisory; not a WCAG requirement",
                                "popup_colors_enabled": bool(popup_present),
                                "vscode_source_parity": native_source,
                                "state_distinctions": state_distinctions(
                                    generated_palette, state_policy,
                                    metadata.get("pane_border_policy", "visible")),
                                "ui_contrast_checks": ui_checks,
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
