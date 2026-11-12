#!/usr/bin/env python3
"""Render installed theme ports with real Spyder/Qt widgets.

Run this with the Python environment that launches Spyder, after exporting and
installing the theme bundle. Source YAML selects the ports/variants to render;
all displayed colors and resources come from the installed theme package.

Example::

    python .tools/render_port_previews.py --out-dir /tmp/spyder-port-previews
    python .tools/render_port_previews.py --out-dir /tmp/tokyo-preview \
        --themes tokyonight tokyo-night-altsynt
    python .tools/render_port_previews.py --out-dir /tmp/pane-preview \
        --themes zenburn --pane-borders
    python .tools/render_port_previews.py --out-dir /tmp/ui-preview \
        --ui-states --pane-borders

The optional pane mode checks real edge pixels and a 1.4:1 thin-frame visibility
heuristic (not WCAG). A theme's explicit ``pane_border_policy: borderless`` skips
only visibility checks; expected border pixels and focus colors are still checked.
The UI-state mode also records current/debug line cleanup, inactive/selected/
hover tabs, ordinary/disabled/hover/pressed buttons, and opted-in menu/Switcher
popups. Its pixel checks use
runtime styles without any test-only color overrides. ``index.html`` and tiled
contact-sheet PNGs make broad visual review practical.

No live Spyder application, projects, consoles, or personal configuration are
opened. Each variant runs in a fresh child process with temporary configuration
and cache directories. At most two children run concurrently, each with a
120-second timeout. PNGs, per-variant logs, and manifest.json are written only
inside the requested output directory.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib
import html
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
WORKERS = 2
TIMEOUT_SECONDS = 120
WINDOW_SIZE = (1180, 900)
PANE_WINDOW_SIZE = (1500, 900)
# A practical thin-frame QA heuristic, not a WCAG accessibility threshold.
MIN_PANE_BORDER_CONTRAST = 1.4
# Advisory only: broad surface fills need review even when their RGB differs.
MIN_SURFACE_CONTRAST = 1.15
UI_STATE_POLICIES = {"distinct-fills", "contrast-borders"}
POPUP_COLOR_ROLES = {
    "COLOR_MENU_BACKGROUND", "COLOR_MENU_TEXT",
    "COLOR_MENU_SELECTED_BACKGROUND", "COLOR_MENU_SELECTED_TEXT",
    "COLOR_MENU_BORDER", "COLOR_SWITCHER_BACKGROUND",
    "COLOR_SWITCHER_SELECTED_BACKGROUND", "COLOR_SWITCHER_BORDER",
    "COLOR_SWITCHER_INPUT_BACKGROUND",
}
MIN_STATE_BORDER_CONTRAST = 3.0
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

# This is parsed/highlighted, never executed. Six nested pairs make every
# optional bracket slot visible, including themes that keep them all identical.
SAMPLE = '''"""Theme preview: documentation and ordinary strings."""
from pathlib import Path
import math

# %% Names, constants, punctuation and six bracket depths
ENABLED = True
values: list[float] = [1.0, 2.5, 3.0]
nested = ((((((values[0]))))))
mapping = {"warm": [1, 2], "cool": (3, 4)}

class Base:
    """A base class with a documentation string."""
    label = "ordinary string"

class Model(Base):
    def transform(self, scale: float = 2.0) -> list[float]:
        """Parameters, built-in types, calls and word operators."""
        if not ENABLED or scale is None:
            return []
        scaled = [round(item * scale, 2) for item in values]
        if scale in values and len(scaled) > 0:
            print(self.label, math.sqrt(scaled[0]))
        return scaled

def summarize(model: Model, limit: int = 3):
    """A function definition and parameter declarations."""
    result = model.transform(2.0)
    return result[:limit] if ENABLED else None

model = Model()
result = summarize(model)
path: Path = Path("preview.py")
print(result, mapping, nested, path.name)
'''


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme-dir", type=Path, default=ROOT)
    parser.add_argument(
        "--spyder-dir", type=Path, default=ROOT.parent / "spyder6_ok97465"
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--themes", nargs="+", metavar="THEME_ID")
    parser.add_argument(
        "--pane-borders", action="store_true",
        help="Render focused editor plus inactive project/Help/console frames and verify their pixels",
    )
    parser.add_argument(
        "--ui-states", action="store_true",
        help="Verify real inactive/hover/selected tabs, button states and current/debug line fills",
    )
    # Internal worker arguments keep Qt/Spyder imports out of the parent.
    parser.add_argument("--_render-one", help=argparse.SUPPRESS)
    parser.add_argument("--_variant", choices=("dark", "light"),
                        help=argparse.SUPPRESS)
    parser.add_argument("--_config-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_result-json", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def _discover(theme_dir: Path, requested: list[str] | None) -> list[dict]:
    """Read every theme's metadata, including the original bundled themes."""
    import yaml

    if requested:
        names = list(dict.fromkeys(requested))
        directories = []
        for name in names:
            # Theme IDs are directory names, not paths supplied to a worker.
            if name in (".", "..") or Path(name).name != name:
                raise ValueError(f"Not a theme ID: {name!r}")
            directory = theme_dir / name
            if not (directory / "theme.yaml").is_file():
                raise ValueError(f"Theme metadata not found: {directory}")
            directories.append(directory)
    else:
        directories = sorted(
            directory for directory in theme_dir.iterdir()
            if directory.is_dir()
            and (directory / "theme.yaml").is_file()
        )

    jobs = []
    for directory in directories:
        metadata = yaml.safe_load((directory / "theme.yaml").read_text())
        variants = metadata.get("variants", {})
        if not isinstance(variants, dict):
            raise ValueError(f"Invalid variants in {directory / 'theme.yaml'}")
        for variant in ("dark", "light"):
            if variants.get(variant) is True:
                jobs.append({
                    "theme": directory.name,
                    "variant": variant,
                    "display_name": metadata.get("display_name", directory.name),
                })
    if not jobs:
        raise ValueError(f"No supported theme variants found in {theme_dir}")
    return jobs


def _relative_luminance(color: str) -> float:
    """Compute sRGB luminance locally; the Spyder runtime needs no ThemeWeaver."""
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045
              else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def _contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((_relative_luminance(first), _relative_luminance(second)),
                         reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _unfocused_frame_border_role(source: str, palette) -> tuple[str, str]:
    """Resolve the actual Help method's unfocused palette path.

    Some Spyder versions use COLOR_BACKGROUND_4 directly; others opt in to
    COLOR_PANE_BORDER with that legacy fallback. Inspect the source rather
    than assuming the optional role is supported because the palette has it.
    Unknown implementations fail explicitly so a runtime change gets reviewed.
    """
    tree = ast.parse(textwrap.dedent(source))

    def resolve(expression):
        if (isinstance(expression, ast.Attribute)
                and isinstance(expression.value, ast.Name)
                and expression.value.id == "SpyderPalette"):
            return expression.attr
        if (isinstance(expression, ast.Call)
                and isinstance(expression.func, ast.Name)
                and expression.func.id == "getattr"
                and len(expression.args) in (2, 3)
                and isinstance(expression.args[0], ast.Name)
                and expression.args[0].id == "SpyderPalette"
                and isinstance(expression.args[1], ast.Constant)
                and isinstance(expression.args[1].value, str)):
            role = expression.args[1].value
            if hasattr(palette, role):
                return role
            if len(expression.args) == 3:
                return resolve(expression.args[2])
        raise RuntimeError("Unrecognized FrameWebView unfocused border expression")

    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "focus"):
            for statement in node.orelse:
                if (isinstance(statement, ast.Assign)
                        and any(isinstance(target, ast.Name)
                                and target.id == "border_color"
                                for target in statement.targets)):
                    return resolve(statement.value), ast.unparse(statement.value)
    raise RuntimeError("FrameWebView unfocused border assignment was not found")


def _measure_pane_border(widget, *, name: str, state: str, role: str,
                         expected: str, outer: str, policy: str,
                         focused: bool = False) -> dict:
    """Check several points on each edge, allowing native overlays/corners.

    The edge color must occur at two positions on at least two distinct edges.
    Border width, rounding, editor gutters and headers can obscure other edges.
    """
    pixmap = widget.grab()
    image = pixmap.toImage()
    width, height = image.width(), image.height()
    depth = max(1, round(2 * pixmap.devicePixelRatioF()))
    expected = expected.lower()
    edge_samples = {}
    matching_edges = []
    for edge in ("top", "right", "bottom", "left"):
        samples = []
        matched_positions = 0
        for fraction in (0.25, 0.5, 0.75):
            colors = []
            for inset in range(depth):
                if edge in ("top", "bottom"):
                    x = min(width - 1, int((width - 1) * fraction))
                    y = inset if edge == "top" else height - 1 - inset
                else:
                    x = inset if edge == "left" else width - 1 - inset
                    y = min(height - 1, int((height - 1) * fraction))
                colors.append(image.pixelColor(x, y).name().lower())
            matched_positions += expected in colors
            samples.append(colors)
        edge_samples[edge] = {"samples": samples,
                              "matched_positions": matched_positions}
        if matched_positions >= 2:
            matching_edges.append(edge)

    # Blank lower/right viewport areas avoid text, gutter, headers and the
    # current line. Several samples avoid treating one glyph as the background.
    viewport = widget.viewport() if hasattr(widget, "viewport") else widget
    background_image = viewport.grab().toImage()
    background_samples = [
        background_image.pixelColor(
            int((background_image.width() - 1) * x),
            int((background_image.height() - 1) * y),
        ).name().lower()
        for x in (0.7, 0.8, 0.9) for y in (0.65, 0.8, 0.9)
    ]
    background = Counter(background_samples).most_common(1)[0][0]
    widget_ratio = _contrast_ratio(expected, background)
    outer_ratio = _contrast_ratio(expected, outer)
    # Borderless is an inactive-frame policy. Keyboard focus must remain
    # visible even when a theme deliberately omits its idle boundaries.
    enforce_visibility = focused or policy == "visible"
    color_passed = len(matching_edges) >= 2
    visibility_passed = (not enforce_visibility or
                         min(widget_ratio, outer_ratio) >= MIN_PANE_BORDER_CONTRAST)
    return {
        "widget": name, "state": state, "role": role,
        "expected_border": expected, "has_focus": widget.hasFocus(),
        "focused_border_check": focused,
        "matching_edges": matching_edges, "edge_samples": edge_samples,
        "pixel_match_passed": color_passed,
        "widget_background": background, "background_samples": background_samples,
        "outer_background": outer.lower(),
        "contrast_with_widget": round(widget_ratio, 3),
        "contrast_with_outer": round(outer_ratio, 3),
        "visibility_enforced": enforce_visibility,
        "minimum_contrast": MIN_PANE_BORDER_CONTRAST,
        "visibility_passed": visibility_passed,
        "passed": color_passed and visibility_passed,
    }


def _measure_fill(widget, *, name: str, state: str, role: str,
                  expected: str, rectangle=None) -> dict:
    """Find the expected fill in real interior pixels, avoiding rounded edges.

    Sample a grid rather than one point: labels, close icons and caret positions
    can cover a single point even when the correct fill is present.
    """
    pixmap = widget.grab()
    image = pixmap.toImage()
    scale = pixmap.devicePixelRatioF()
    if rectangle is None:
        rectangle = (4, 4, widget.width() - 8, widget.height() - 8)
    x, y, width, height = rectangle
    colors = [
        image.pixelColor(
            min(image.width() - 1, max(0, round((x + width * fx) * scale))),
            min(image.height() - 1, max(0, round((y + height * fy) * scale))),
        ).name().lower()
        for fx in (0.08, 0.18, 0.32, 0.48, 0.65, 0.82, 0.92)
        for fy in (0.12, 0.28, 0.5, 0.72, 0.88)
    ]
    counts = Counter(colors)
    expected = expected.lower()
    matching = counts[expected]
    return {
        "widget": name, "state": state, "role": role,
        "expected_fill": expected, "observed_fill": counts.most_common(1)[0][0],
        "sample_count": len(colors), "matching_samples": matching,
        "colors": dict(counts), "passed": matching >= len(colors) * 0.25,
    }


def _measure_control_border(widget, *, name: str, state: str, role: str,
                            expected: str, rectangle=None, edges=None) -> dict:
    """Check real control edge pixels independently of equal interior fills.

    Buttons need two matching edges; a tab's orientation-specific accent must
    appear on its declared edge. Sampling several positions avoids labels and
    rounded corners. No test stylesheet or painter supplies the expected color.
    """
    pixmap = widget.grab()
    image = pixmap.toImage()
    scale = pixmap.devicePixelRatioF()
    if rectangle is None:
        rectangle = (0, 0, widget.width(), widget.height())
    x, y, width, height = rectangle
    left, top = round(x * scale), round(y * scale)
    right, bottom = round((x + width) * scale) - 1, round((y + height) * scale) - 1
    expected = expected.lower()
    edge_samples = {}
    matching_edges = []
    for edge in edges or ("top", "right", "bottom", "left"):
        samples = []
        for fraction in (0.25, 0.5, 0.75):
            colors = []
            for inset in range(max(1, round(3 * scale))):
                if edge in ("top", "bottom"):
                    px = round(left + (right - left) * fraction)
                    py = top + inset if edge == "top" else bottom - inset
                else:
                    px = left + inset if edge == "left" else right - inset
                    py = round(top + (bottom - top) * fraction)
                px = min(image.width() - 1, max(0, px))
                py = min(image.height() - 1, max(0, py))
                colors.append(image.pixelColor(px, py).name().lower())
            samples.append(colors)
        matches = sum(expected in colors for colors in samples)
        edge_samples[edge] = {"samples": samples, "matched_positions": matches}
        if matches >= 2:
            matching_edges.append(edge)
    required = len(edges) if edges else 2
    return {
        "widget": name, "state": state, "role": role,
        "expected_border": expected, "matching_edges": matching_edges,
        "sampled_rectangle": list(rectangle),
        "required_matching_edges": required, "edge_samples": edge_samples,
        "passed": len(matching_edges) >= required,
    }


def _tab_border_rectangle(bar, index: int, position: str) -> tuple:
    """Exclude the real tab stylesheet's margins from its layout rectangle.

    Qt's tabRect includes margins: pane tabs have a 12 px top margin and dock
    tabs have a 6 px bottom margin. Their accent is on the border box inside
    that space, rather than on the outer layout edge. Resolve these properties
    from the applied local sheet; do not search arbitrary interior pixels for
    an expected accent color.
    """
    from qstylizer.parser import parse

    # Pane tabs inherit their local sheet from QTabWidget; standalone dock
    # bars own it directly. Inspect the same sheet Qt uses in each case.
    stylesheet = bar.styleSheet()
    if not stylesheet and bar.parentWidget() is not None:
        stylesheet = bar.parentWidget().styleSheet()
    css = parse(stylesheet)
    margins = [0, 0, 0, 0]  # top, right, bottom, left

    def pixels(value):
        value = str(value).strip()
        if value.endswith("px"):
            value = value[:-2]
        return int(value)

    for selector in (
        "QTabBar::tab", f"QTabBar::tab:{position}",
        "QTabBar::tab:selected", f"QTabBar::tab:{position}:selected",
    ):
        rule = css[selector]
        shorthand = rule.margin.value
        if shorthand is not None:
            values = [pixels(value) for value in str(shorthand).split()]
            if len(values) == 1:
                margins = values * 4
            elif len(values) == 2:
                margins = values * 2
            elif len(values) == 3:
                margins = [values[0], values[1], values[2], values[1]]
            elif len(values) == 4:
                margins = values
            else:
                raise RuntimeError(f"Unsupported tab margin: {shorthand!r}")
        for i, property_name in enumerate((
            "marginTop", "marginRight", "marginBottom", "marginLeft"
        )):
            value = getattr(rule, property_name).value
            if value is not None:
                margins[i] = pixels(value)
    rect = bar.tabRect(index)
    top, right, bottom, left = margins
    return (rect.x() + left, rect.y() + top,
            rect.width() - left - right, rect.height() - top - bottom)


def _measure_text_color(widget, *, name, state, role, expected, background,
                        rectangle, actual_text, html_color=None) -> dict:
    """Inspect actual glyph pixels; HTML-delegate colors are inspected too.

    Palette values alone miss QMenu selected-state selectors, and Qt's
    highlighted-text palette does not override Switcher's explicit HTML spans.
    A glyph region excludes the surrounding frame so matching border pixels
    cannot masquerade as foreground text.
    """
    pixmap = widget.grab()
    image = pixmap.toImage()
    scale = pixmap.devicePixelRatioF()
    x, y, width, height = rectangle
    left, top = max(0, round(x * scale)), max(0, round(y * scale))
    right = min(image.width(), round((x + width) * scale))
    bottom = min(image.height(), round((y + height) * scale))
    counts = Counter(
        image.pixelColor(px, py).name().lower()
        for py in range(top, bottom) for px in range(left, right)
    )
    expected = expected.lower()
    exact = counts[expected]
    strongest = max(counts, key=lambda color: _contrast_ratio(color, background))
    html_passed = html_color is None or html_color.lower() == expected
    ratio = _contrast_ratio(expected, background)
    return {
        "widget": name, "state": state, "role": role, "kind": "text",
        "actual_text": actual_text, "expected_text_color": expected,
        "observed_text_color": expected if exact else strongest,
        "exact_foreground_pixels": exact,
        "html_fragment_color": html_color,
        "html_color_passed": html_passed,
        "background": background.lower(), "contrast": round(ratio, 3),
        "minimum_contrast": 4.5,
        "sampled_rectangle": list(rectangle),
        "passed": bool(actual_text) and exact >= 2 and html_passed and ratio >= 4.5,
    }


def _render_popup_states(app, window, palette, args, settle,
                         state_policy="distinct-fills") -> dict:
    """Exercise actual QMenu and Spyder Switcher without stylesheet overrides."""
    present = {role for role in POPUP_COLOR_ROLES if hasattr(palette, role)}
    if not present:
        return {
            "enabled": False, "passed": True, "checks": [], "captures": [],
            "limitations": ["Legacy theme has not opted into popup color roles."],
        }
    if present != POPUP_COLOR_ROLES:
        raise RuntimeError(f"Incomplete popup color bundle: {sorted(POPUP_COLOR_ROLES - present)}")

    from qtpy.QtCore import QPoint, Qt
    from qtpy.QtGui import QPalette, QTextDocument
    from qtpy.QtTest import QTest
    from qtpy.QtWidgets import QMenu
    from spyder.plugins.switcher.widgets.switcher import Switcher

    checks, captures = [], []

    def capture(widget, suffix):
        name = f"{args._render_one}--{args._variant}--{suffix}.png"
        if not widget.grab().save(str(args.out_dir / name), "PNG"):
            raise RuntimeError(f"Could not save {name}")
        captures.append(name)

    def rect_tuple(rect):
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def fill(widget, name, state, role, rectangle=None):
        result = _measure_fill(
            widget, name=name, state=state, role=role,
            expected=getattr(palette, role), rectangle=rectangle,
        )
        checks.append(result)
        return result

    menu = QMenu(window)
    actions = [menu.addAction(text) for text in (
        "Open preview file", "Find symbols in preview", "Theme preferences",
    )]
    menu.popup(window.mapToGlobal(QPoint(35, 75)))
    settle()
    QTest.mouseMove(menu, menu.actionGeometry(actions[1]).center())
    settle()
    menu_activation = "mouse hover"
    if menu.activeAction() != actions[1]:
        QTest.keyClick(menu, Qt.Key_Down)
        settle()
        menu_activation = "keyboard navigation"
    if menu.activeAction() != actions[1]:
        # Offscreen platforms cannot always grab the keyboard or route hover.
        # Use QMenu's real state API; its stylesheet and painter stay intact.
        menu.setActiveAction(actions[1])
        settle()
        menu_activation = "QMenu.setActiveAction (offscreen input fallback)"
    if menu.activeAction() != actions[1]:
        raise RuntimeError("Real QMenu hover did not activate the selected action")
    for index, state, bg_role, text_role in (
        (0, "normal", "COLOR_MENU_BACKGROUND", "COLOR_MENU_TEXT"),
        (1, "selected", "COLOR_MENU_SELECTED_BACKGROUND", "COLOR_MENU_SELECTED_TEXT"),
    ):
        rect = menu.actionGeometry(actions[index])
        measured = fill(menu, "menu", state, bg_role,
                        rect_tuple(rect.adjusted(4, 3, -4, -3)))
        checks.append(_measure_text_color(
            menu, name="menu", state=state + "_text", role=text_role,
            expected=getattr(palette, text_role),
            background=measured["observed_fill"],
            rectangle=rect_tuple(rect.adjusted(20, 3, -12, -3)),
            actual_text=actions[index].text(),
        ))
    checks.append(_measure_control_border(
        menu, name="menu", state="border", role="COLOR_MENU_BORDER",
        expected=palette.COLOR_MENU_BORDER,
    ))
    if hasattr(palette, "COLOR_MENU_SELECTED_BORDER"):
        checks.append(_measure_control_border(
            menu, name="menu", state="selected_border",
            role="COLOR_MENU_SELECTED_BORDER",
            expected=palette.COLOR_MENU_SELECTED_BORDER,
            rectangle=rect_tuple(menu.actionGeometry(actions[1])),
        ))
    capture(menu, "menu-popup")
    menu.close()
    settle()

    switcher = None
    switcher_diagnostics = {}
    try:
        switcher = Switcher(window, help_text="Search preview commands")
        titles = ("Preview: Open file", "Preview: Find symbol", "Preview: Run analysis")
        for title in titles:
            switcher.add_item(title=title, description="isolated UI preview",
                              last_item=title == titles[-1])
        switcher.set_search_text("Preview")
        switcher.setup()
        switcher.set_current_row(1)
        switcher.move(window.mapToGlobal(QPoint(65, 100)))
        switcher.show()
        switcher.edit.setFocus()
        settle()
        if switcher.current_row() != 1 or not switcher.edit.hasFocus():
            raise RuntimeError("Real Switcher did not preserve selected row and input focus")
        palette_roles = {
            "Base": QPalette.Base, "Window": QPalette.Window,
            "Highlight": QPalette.Highlight, "Text": QPalette.Text,
            "HighlightedText": QPalette.HighlightedText,
        }
        switcher_diagnostics["list_palette"] = {
            name: switcher.list.palette().color(role).name()
            for name, role in palette_roles.items()
        }
        switcher_diagnostics["dialog_meta_class"] = switcher.metaObject().className()
        switcher_diagnostics["list_parent_meta_class"] = (
            switcher.list.parentWidget().metaObject().className()
        )
        switcher_diagnostics["list_local_stylesheet"] = switcher.list.styleSheet()
        switcher_diagnostics["dialog_local_stylesheet"] = switcher.styleSheet()
        switcher_diagnostics["applied_switcher_rules"] = [
            rule.strip() + "}" for rule in app.styleSheet().split("}")
            if "Switcher" in rule
        ]
        if hasattr(switcher.list, "viewOptions"):
            option = switcher.list.viewOptions()
            switcher_diagnostics["view_option_palette"] = {
                name: option.palette.color(role).name()
                for name, role in palette_roles.items()
            }
            switcher_diagnostics["view_option_widget"] = (
                option.widget.metaObject().className() if option.widget else None
            )
        viewport = switcher.list.viewport()
        fill(switcher, "switcher", "background", "COLOR_SWITCHER_BACKGROUND",
             (4, switcher.height() - 8, switcher.width() - 8, 3))
        input_fill = fill(switcher.edit, "switcher_input", "normal",
                          "COLOR_SWITCHER_INPUT_BACKGROUND")
        input_text_color = switcher.edit.palette().color(QPalette.Text).name().lower()
        input_text_check = _measure_text_color(
            switcher.edit, name="switcher_input", state="text", role="COLOR_TEXT_1",
            expected=palette.COLOR_TEXT_1, background=input_fill["observed_fill"],
            rectangle=(6, 4, switcher.edit.width() - 12, switcher.edit.height() - 8),
            actual_text=switcher.edit.text(),
        )
        input_text_check["qt_palette_text_color"] = input_text_color
        input_text_check["passed"] &= input_text_color == palette.COLOR_TEXT_1.lower()
        checks.append(input_text_check)
        row_fills = {}
        selected_rect = None
        for row, state, bg_role in (
            (0, "normal", "COLOR_SWITCHER_BACKGROUND"),
            (1, "selected", "COLOR_SWITCHER_SELECTED_BACKGROUND"),
        ):
            index = switcher.proxy.index(row, 0)
            rect = switcher.list.visualRect(index)
            measured = fill(viewport, "switcher_list", state, bg_role,
                            rect_tuple(rect.adjusted(3, 2, -3, -2)))
            row_fills[state] = measured["observed_fill"]
            if state == "selected":
                selected_rect = rect
            item = switcher.model.item(switcher.proxy.mapToSource(index).row())
            document = QTextDocument()
            document.setHtml(item.text())
            title_cursor = document.find(item.get_title())
            if title_cursor.isNull():
                raise RuntimeError("Switcher title was absent from the real row HTML")
            html_color = title_cursor.charFormat().foreground().color().name().lower()
            checks.append(_measure_text_color(
                viewport, name="switcher_list", state=state + "_html_text",
                role="COLOR_TEXT_1", expected=palette.COLOR_TEXT_1,
                background=measured["observed_fill"],
                rectangle=rect_tuple(rect.adjusted(8, 3, -8, -3)),
                actual_text=item.get_title(), html_color=html_color,
            ))
        selected_outline = None
        if hasattr(palette, "COLOR_SWITCHER_SELECTED_BORDER"):
            selected_outline = _measure_control_border(
                viewport, name="switcher_list", state="selected_border",
                role="COLOR_SWITCHER_SELECTED_BORDER",
                expected=palette.COLOR_SWITCHER_SELECTED_BORDER,
                rectangle=rect_tuple(selected_rect),
            )
            checks.append(selected_outline)
        if state_policy == "contrast-borders":
            # Equal fills are valid only when a real, visible outline marks
            # the selected row. Verify pixels instead of the role declaration.
            ratio = _contrast_ratio(row_fills["normal"], row_fills["selected"])
            outline_ratio = min(
                _contrast_ratio(palette.COLOR_SWITCHER_SELECTED_BORDER, color)
                for color in row_fills.values()
            ) if selected_outline else 0.0
            checks.append({
                "widget": "switcher_list", "state": "selection_indicator",
                "role": "COLOR_SWITCHER_SELECTED_BACKGROUND",
                "normal_fill": row_fills["normal"],
                "selected_fill": row_fills["selected"],
                "contrast": round(ratio, 3), "minimum_contrast": 3.0,
                "outline_contrast": round(outline_ratio, 3),
                "passed": ratio >= 3.0 or bool(
                    selected_outline and selected_outline["passed"]
                    and outline_ratio >= 3.0
                ),
            })
        checks.append(_measure_control_border(
            switcher, name="switcher", state="border", role="COLOR_SWITCHER_BORDER",
            expected=palette.COLOR_SWITCHER_BORDER,
        ))
        capture(switcher, "switcher-popup")
    except Exception as exc:
        # Preserve the genuine menu/main captures if a companion Switcher API
        # cannot run in this Qt build. Report the limitation; never substitute a
        # mock dialog or patch the application's class to manufacture pixels.
        checks.append({
            "widget": "switcher", "state": "runtime", "role": "Switcher runtime",
            "passed": False, "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        })
        if switcher is not None:
            capture(switcher, "switcher-runtime-error")
    finally:
        if switcher is not None:
            switcher.close()
        settle()
    failures = [f"{check['widget']}/{check['state']}: {check['role']}"
                for check in checks if not check["passed"]]
    return {
        "enabled": True, "passed": not failures, "checks": checks,
        "captures": captures, "failures": failures,
        "switcher_class": "spyder.plugins.switcher.widgets.switcher.Switcher",
        "switcher_source": inspect.getsourcefile(Switcher),
        "switcher_text_basis": "Actual row HTML and rendered glyph pixels; no highlighted-text override",
        "switcher_diagnostics": switcher_diagnostics,
        "menu_activation": menu_activation,
        "limitations": [
            "Switcher sections are empty in this command preview; section-label accent contrast is not asserted.",
            "Popup geometry is isolated; native OS shadows are not part of the color checks.",
        ],
    }


def _render_one(args: argparse.Namespace) -> dict:
    """Initialize an isolated real Qt application and capture its widgets."""
    if args._config_dir is None or args._result_json is None or not args._variant:
        raise ValueError("Internal render arguments are incomplete")

    # These settings precede every Qt/Spyder import. Do not inherit a test/safe
    # mode flag that could redirect Spyder to its shared clean config directory.
    config_dir = args._config_dir.resolve()
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SPYDER_CONFDIR"] = str(config_dir)
    os.environ["SPYDER_USE_DEV_CONFIG_DIR"] = "false"
    os.environ.pop("SPYDER_PYTEST", None)
    os.environ.pop("SPYDER_SAFE_MODE", None)
    os.environ["XDG_CONFIG_HOME"] = str(config_dir / "xdg-config")
    os.environ["XDG_CACHE_HOME"] = str(config_dir / "cache")
    os.environ["MPLCONFIGDIR"] = str(config_dir / "matplotlib")
    os.environ["IPYTHONDIR"] = str(config_dir / "ipython")
    os.environ["JUPYTER_CONFIG_DIR"] = str(config_dir / "jupyter")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.spyder_dir.resolve()))
    # Any library command-line inspection should see no renderer-only flags.
    sys.argv = [str(Path(__file__).resolve())]

    from spyder.config.manager import CONF

    scheme = f"spyder_themes.{args._render_one}/{args._variant}"
    CONF.set("appearance", "selected", scheme)
    CONF.set("appearance", "ui_theme", args._variant)

    import qtpy
    from qtpy.QtCore import QFile, QPoint, QSize, Qt, qVersion
    from qtpy.QtGui import QFontDatabase, QTextCursor
    from qtpy.QtTest import QTest
    from qtpy.QtWidgets import (
        QApplication, QFrame, QLabel, QMainWindow, QPlainTextEdit,
        QPushButton, QSplitter, QStyle, QTabBar,
        QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
    )

    if args.pane_borders:
        # QtWebEngine must be imported before QApplication on some Qt builds.
        # Import the real method but never construct a WebView/WebEngine widget.
        from spyder.widgets.browser import FrameWebView

    app = QApplication([])
    app.setStyle("Fusion")
    ui_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
    ui_font.setPointSize(10)
    app.setFont(ui_font)

    from spyder.utils.theme_manager import (
        OPTIONAL_PYTHON_SCHEME_KEYS, THEME_MANAGER,
    )
    from spyder.utils.palette import SpyderPalette
    from spyder.utils.stylesheet import (
        APP_STYLESHEET, APP_TOOLBAR_STYLESHEET,
        HORIZONTAL_DOCK_TABBAR_STYLESHEET, PANES_TABBAR_STYLESHEET,
    )
    from spyder.plugins.editor.widgets.codeeditor.codeeditor import CodeEditor
    import spyder

    # Resource loading before QApplication exists can crash some Qt builds.
    # Palette import may defer resources, so explicitly finish that work now.
    THEME_MANAGER.load_pending_resources()
    app.setStyleSheet(str(APP_STYLESHEET))
    THEME_MANAGER.load_pending_resources()
    theme_module = importlib.import_module(f"spyder_themes.{args._render_one}")
    installed_root = Path(theme_module.__file__).resolve().parent
    expected_palette = getattr(theme_module, f"SpyderPalette{args._variant.title()}")
    import yaml

    metadata = yaml.safe_load(
        (args.theme_dir / args._render_one / "theme.yaml").read_text()
    )
    state_policy = metadata.get("ui_state_policy", "distinct-fills")
    if state_policy not in UI_STATE_POLICIES:
        raise ValueError(f"Invalid ui_state_policy: {state_policy!r}")
    if SpyderPalette.EDITOR_BACKGROUND != expected_palette.EDITOR_BACKGROUND:
        raise RuntimeError("The selected runtime palette does not match the requested variant")

    warnings = []
    try:
        from spyder.utils.icon_manager import ima
    except Exception as exc:
        ima = None
        warnings.append(f"Spyder icons unavailable; using Qt standard icons: {exc}")

    def icon(name, standard):
        if ima is not None:
            try:
                actual = ima.icon(name)
                if actual is not None and not actual.isNull():
                    return actual
            except Exception as exc:
                warnings.append(f"Icon {name}: {exc}")
        return app.style().standardIcon(standard)

    window = QMainWindow()
    window.setWindowTitle(f"{args._render_one} / {args._variant} — real Spyder widgets")
    window.resize(*(PANE_WINDOW_SIZE if args.pane_borders else WINDOW_SIZE))

    toolbar = QToolBar("Application toolbar", window)
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(22, 22))
    toolbar.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))
    toolbar.addWidget(QLabel(f"  {args._render_one}  /  {args._variant}    "))
    for label, name, fallback in (
        ("New", "filenew", QStyle.SP_FileIcon),
        ("Open", "fileopen", QStyle.SP_DirOpenIcon),
        ("Save", "filesave", QStyle.SP_DialogSaveButton),
        ("Run", "run", QStyle.SP_MediaPlay),
        ("Stop", "stop", QStyle.SP_MediaStop),
        ("Preferences", "configure", QStyle.SP_FileDialogDetailedView),
    ):
        toolbar.addAction(icon(name, fallback), label)
    window.addToolBar(toolbar)

    central = QWidget(window)
    layout = QVBoxLayout(central)
    layout.setContentsMargins(4, 4, 4, 0)
    layout.setSpacing(3)
    splitter = QSplitter(Qt.Horizontal, central)
    sidebar = QWidget(splitter)
    sidebar_layout = QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(0, 0, 0, 0)
    sidebar_layout.setSpacing(6)

    tree = QTreeWidget(sidebar)
    tree.setHeaderLabel("FOLDERS · active selection")
    if args.pane_borders:
        tree.setHeaderLabel("Project · inactive")
    tree.setIndentation(16)
    tree.setMouseTracking(True)
    project = QTreeWidgetItem(tree, ["Scientific"])
    project.setIcon(0, icon("DirOpenIcon", QStyle.SP_DirOpenIcon))
    selected = None
    for name in (".spyproject", "__pycache__", "data", "doc", "scripts",
                 "preview.py", "analysis.py", "README.md"):
        item = QTreeWidgetItem(project, [name])
        is_file = "." in name and not name.startswith(".")
        item.setIcon(0, icon("filenew" if is_file else "DirClosedIcon",
                             QStyle.SP_FileIcon if is_file else QStyle.SP_DirIcon))
        if name == "preview.py":
            selected = item
    tree.expandAll()
    tree.setCurrentItem(selected)
    sidebar_layout.addWidget(tree, 1)

    inactive_tree = QTreeWidget(sidebar)
    inactive_tree.setHeaderLabel("Inactive selection")
    inactive_tree.setFixedHeight(122)
    for name in ("preview.py", "analysis.py", "notes.txt"):
        QTreeWidgetItem(inactive_tree, [name])
    inactive_tree.setCurrentItem(inactive_tree.topLevelItem(0))
    sidebar_layout.addWidget(inactive_tree)

    normal_button = hover_button = pressed_button = disabled_button = None
    if args.ui_states:
        controls = QWidget(sidebar)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(4, 4, 4, 4)
        controls_layout.addWidget(QLabel("Buttons · real Qt states"))
        normal_button = QPushButton("Normal", controls)
        hover_button = QPushButton("Hover", controls)
        pressed_button = QPushButton("Pressed", controls)
        disabled_button = QPushButton("Disabled", controls)
        disabled_button.setEnabled(False)
        for button in (normal_button, hover_button, pressed_button, disabled_button):
            button.setFocusPolicy(Qt.NoFocus)
            controls_layout.addWidget(button)
        sidebar_layout.addWidget(controls)

    tabs = QTabWidget(splitter)
    tabs.setDocumentMode(True)
    tabs.setTabsClosable(True)
    tabs.tabBar().setExpanding(False)
    tabs.setStyleSheet(str(PANES_TABBAR_STYLESHEET))
    tabs.addTab(QWidget(), "notes.py")
    editor = CodeEditor(None)
    editor_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    editor_font.setPointSize(11)
    editor.setup_editor(
        language="Python", linenumbers=True, markers=False, folding=False,
        scrollflagarea=False, edge_line=False, show_blanks=False,
        automatic_completions=False, completions_hint=False, hover_hints=False,
        code_snippets=False, show_class_func_dropdown=False,
        highlight_current_cell=False, font=editor_font,
        filename=str(config_dir / "preview.py"), color_scheme=scheme,
    )
    editor.set_text(SAMPLE)
    editor.highlighter.rehighlight()
    breakpoint_manager = None
    if args.ui_states:
        editor.go_to_line(7)
    if args.ui_states and hasattr(SpyderPalette, "EDITOR_DEBUGLINE"):
        from spyder.plugins.debugger.panels.debuggerpanel import DebuggerPanel
        from spyder.plugins.debugger.utils.breakpointsmanager import BreakpointsManager

        editor.panels.register(DebuggerPanel())
        breakpoint_manager = BreakpointsManager(editor)
        breakpoint_manager.update_pdb_state(True, editor.filename, 10)
    # Verify the installed palette survives ThemeManager and CodeEditor setup.
    # Looking only at exported YAML would miss stale or overridden formats.
    for role in OPTIONAL_PYTHON_SCHEME_KEYS:
        expected = getattr(expected_palette, "EDITOR_" + role.upper())
        actual = editor.highlighter.formats[role]
        observed = (actual.foreground().color().name().lower(),
                    actual.font().bold(), actual.fontItalic())
        required = (expected[0].lower(), expected[1], expected[2])
        if observed != required:
            raise RuntimeError(f"Runtime format mismatch for {role}: {observed} != {required}")
    tabs.addTab(editor, "preview.py")
    tabs.addTab(QWidget(), "data.py")
    tabs.setCurrentIndex(1)
    splitter.addWidget(sidebar)
    splitter.addWidget(tabs)
    help_frame = console = None
    if args.pane_borders:
        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_layout.addWidget(QLabel("Help · inactive"))
        help_frame = QFrame(right)
        help_layout = QVBoxLayout(help_frame)
        help_layout.setContentsMargins(12, 12, 12, 12)
        help_label = QLabel(
            "<b>numpy.ndarray</b><br><br>"
            "An array object with a shape and a dtype.<br><br>"
            "<b>Parameters</b><br>"
            "shape: tuple of integers<br>"
            "dtype: data type, optional", help_frame,
        )
        help_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        help_label.setWordWrap(True)
        # QLabel inherits QFrame; emulate a web page body without an extra
        # nested frame from the real QFrame stylesheet selector.
        help_label.setStyleSheet("border: none;")
        help_layout.addWidget(help_label)
        FrameWebView._apply_stylesheet(help_frame, focus=False)
        right_layout.addWidget(help_frame, 1)
        right_layout.addWidget(QLabel("IPython console · inactive"))
        console = QPlainTextEdit(right)
        console.setFont(editor_font)
        console.setPlainText(
            "Python · isolated preview\n\nIn [1]: import numpy as np\n"
            "In [2]: np.arange(4)\nOut[2]: array([0, 1, 2, 3])\n"
        )
        right_layout.addWidget(console, 1)
        splitter.addWidget(right)
        splitter.setSizes([245, 790, 440])
    else:
        splitter.setSizes([235, 930])
    layout.addWidget(splitter, 1)

    dock_tabs = QTabBar(central)
    dock_tabs.setShape(QTabBar.RoundedSouth)
    dock_tabs.setExpanding(False)
    dock_tabs.setStyleSheet(str(HORIZONTAL_DOCK_TABBAR_STYLESHEET))
    for label in ("Help", "Variable Explorer", "Debugger", "Plots", "Files"):
        dock_tabs.addTab(label)
    dock_tabs.setCurrentIndex(1)
    layout.addWidget(dock_tabs)
    window.setCentralWidget(central)
    status = window.statusBar()
    status.showMessage(
        ("Current line: 7 · "
         + ("Paused debugger: 10 · " if breakpoint_manager is not None else "")
         + "isolated real Qt widgets")
        if args.ui_states else "Ready · isolated preview · six nested bracket levels"
    )
    status.addPermanentWidget(QLabel("Python   |   Spaces: 4   |   UTF-8  "))

    window.show()
    window.activateWindow()
    # One tree has an active selection, the second an inactive selection. Both
    # use the real stylesheet paths; their backgrounds are never painted here.
    (editor if args.pane_borders or args.ui_states else tree).setFocus()
    editor.verticalScrollBar().setValue(0)
    for _ in range(6):
        app.processEvents()
        time.sleep(0.025)

    def settle():
        for _ in range(4):
            app.processEvents()
            time.sleep(0.02)

    pane_border_checks = None
    if args.pane_borders:
        policy = metadata.get("pane_border_policy", "visible")
        if policy not in ("visible", "borderless"):
            raise ValueError(f"Invalid pane_border_policy: {policy!r}")
        outer = SpyderPalette.COLOR_BACKGROUND_1
        legacy = SpyderPalette.COLOR_BACKGROUND_4
        pane = getattr(SpyderPalette, "COLOR_PANE_BORDER", legacy)
        editor_border = getattr(SpyderPalette, "COLOR_EDITOR_BORDER", pane)
        sidebar_border = getattr(SpyderPalette, "COLOR_SIDEBAR_BORDER", pane)
        help_border_role, help_border_expression = _unfocused_frame_border_role(
            inspect.getsource(FrameWebView._apply_stylesheet), SpyderPalette
        )
        help_border = getattr(SpyderPalette, help_border_role)
        checks = []
        focus_states = {}

        def focus_state():
            return {"editor": editor.hasFocus(), "project": tree.hasFocus(),
                    "help": help_frame.hasFocus(), "console": console.hasFocus()}

        focus_states["editor_focused"] = focus_state()
        for name, widget, role, color in (
            ("project", tree, "COLOR_SIDEBAR_BORDER", sidebar_border),
            ("help", help_frame, help_border_role, help_border),
            ("console", console, "COLOR_PANE_BORDER", pane),
            ("editor", editor, "COLOR_ACCENT_3", SpyderPalette.COLOR_ACCENT_3),
        ):
            checks.append(_measure_pane_border(
                widget, name=name, state="editor_focused", role=role,
                expected=color, outer=outer, policy=policy, focused=name == "editor",
            ))
        console.setFocus()
        settle()
        focus_states["console_focused"] = focus_state()
        for name, widget, role, color in (
            ("editor", editor, "COLOR_EDITOR_BORDER", editor_border),
            ("console", console, "COLOR_ACCENT_3", SpyderPalette.COLOR_ACCENT_3),
        ):
            checks.append(_measure_pane_border(
                widget, name=name, state="console_focused", role=role,
                expected=color, outer=outer, policy=policy, focused=name == "console",
            ))
        editor.setFocus()
        settle()
        focus_states["overview"] = focus_state()
        failures = [
            f"{check['state']}/{check['widget']}: "
            f"pixels={check['pixel_match_passed']}, visibility={check['visibility_passed']}"
            for check in checks if not check["passed"]
        ]
        if focus_states["editor_focused"] != {
                "editor": True, "project": False, "help": False, "console": False}:
            failures.append("Initial editor-focused layout did not establish required focus")
        if focus_states["console_focused"]["editor"] or not focus_states["console_focused"]["console"]:
            failures.append("Console focus did not deactivate the CodeEditor")
        if not focus_states["overview"]["editor"]:
            failures.append("Overview did not restore CodeEditor focus")
        pane_border_checks = {
            "policy": policy,
            "minimum_contrast": MIN_PANE_BORDER_CONTRAST,
            "contrast_basis": "Thin-frame QA heuristic; not a WCAG requirement",
            "help_style": "FrameWebView._apply_stylesheet unbound on QFrame; no WebEngine widget",
            "help_border_source": {
                "method": "FrameWebView._apply_stylesheet",
                "file": inspect.getsourcefile(FrameWebView._apply_stylesheet),
                "method_line": inspect.getsourcelines(FrameWebView._apply_stylesheet)[1],
                "unfocused_expression": help_border_expression,
                "resolved_role": help_border_role,
                "resolved_color": help_border,
            },
            "legacy_fallback": legacy,
            "focus_states": focus_states, "checks": checks,
            "passed": not failures, "failures": failures,
        }
    ui_state_checks = None
    if args.ui_states:
        checks = []
        captures = []

        def capture(suffix):
            name = f"{args._render_one}--{args._variant}--{suffix}.png"
            if not window.grab().save(str(args.out_dir / name), "PNG"):
                raise RuntimeError(f"Could not save {name}")
            captures.append(name)

        def fill(widget, name, state, role, rectangle=None):
            if not hasattr(SpyderPalette, role):
                checks.append({"widget": name, "state": state, "role": role,
                               "passed": False, "error": "Missing runtime palette role"})
                return
            result = _measure_fill(
                widget, name=name, state=state, role=role,
                expected=getattr(SpyderPalette, role), rectangle=rectangle,
            )
            if role in ("COLOR_TOOLBAR_BACKGROUND", "COLOR_TAB_BACKGROUND",
                        "COLOR_BUTTON_BACKGROUND"):
                result["surface_visibility"] = []
                for background_role in ("COLOR_BACKGROUND_1", "EDITOR_BACKGROUND"):
                    background = getattr(SpyderPalette, background_role)
                    ratio = _contrast_ratio(result["observed_fill"], background)
                    result["surface_visibility"].append({
                        "background_role": background_role,
                        "background": background,
                        "observed_fill_contrast": round(ratio, 3),
                        "minimum_visibility_advisory": MIN_SURFACE_CONTRAST,
                        "visibility_advisory_passed": ratio >= MIN_SURFACE_CONTRAST,
                    })
            checks.append(result)

        def tab_fill(bar, index, name, state, role):
            rect = bar.tabRect(index).adjusted(4, 4, -4, -4)
            fill(bar, name, state, role,
                 (rect.x(), rect.y(), rect.width(), rect.height()))

        # Use real enter/leave and mouse events: stylesheet state precedence is
        # the failure this catches; injecting a test stylesheet would hide it.
        QTest.mouseMove(window, QPoint(window.width() - 6, 6))
        settle()
        # The empty right side avoids action icons, labels and child buttons.
        fill(toolbar, "toolbar", "normal", "COLOR_TOOLBAR_BACKGROUND",
             (toolbar.width() * 0.8, 4, toolbar.width() * 0.18,
              max(2, toolbar.height() - 8)))
        fill(normal_button, "button", "normal", "COLOR_BUTTON_BACKGROUND")
        fill(disabled_button, "button", "disabled", "COLOR_BUTTON_BACKGROUND")
        if hasattr(SpyderPalette, "COLOR_BUTTON_BORDER"):
            checks.append(_measure_control_border(
                normal_button, name="button", state="normal_border",
                role="COLOR_BUTTON_BORDER", expected=SpyderPalette.COLOR_BUTTON_BORDER,
            ))
        for bar, name in ((tabs.tabBar(), "editor_tabs"), (dock_tabs, "dock_tabs")):
            tab_fill(bar, 0, name, "inactive", "COLOR_TAB_BACKGROUND")
            tab_fill(bar, 1, name, "selected", "COLOR_TAB_SELECTED_BACKGROUND")
            if hasattr(SpyderPalette, "COLOR_TAB_SELECTED_ACCENT"):
                inner = getattr(SpyderPalette, "TAB_SELECTED_ACCENT_INNER_EDGE", 0)
                edge = "bottom" if name == "dock_tabs" else "top"
                rectangle = _tab_border_rectangle(bar, 1, edge)
                if inner:
                    edge = "top" if edge == "bottom" else "bottom"
                checks.append(_measure_control_border(
                    bar, name=name, state="selected_accent",
                    role="COLOR_TAB_SELECTED_ACCENT",
                    expected=SpyderPalette.COLOR_TAB_SELECTED_ACCENT,
                    rectangle=rectangle,
                    edges=(edge,),
                ))

        def line_fill(number, role, state):
            cursor = QTextCursor(editor.document().findBlockByNumber(number - 1))
            rect = editor.cursorRect(cursor)
            viewport = editor.viewport()
            fill(viewport, "editor", state, role,
                 (viewport.width() * 0.75, rect.y() + 2,
                  viewport.width() * 0.2, max(2, rect.height() - 4)))

        line_fill(7, "EDITOR_CURRENTLINE", "current_line")
        if breakpoint_manager is not None:
            line_fill(10, "EDITOR_DEBUGLINE", "debug_line")
        line_fill(9, "EDITOR_BACKGROUND", "ordinary_line")
        capture("normal")

        QTest.mouseMove(hover_button, hover_button.rect().center())
        settle()
        fill(hover_button, "button", "hover", "COLOR_BUTTON_HOVER_BACKGROUND")
        capture("button-hover")
        QTest.mouseMove(pressed_button, pressed_button.rect().center())
        QTest.mousePress(pressed_button, Qt.LeftButton,
                         pos=pressed_button.rect().center())
        settle()
        fill(pressed_button, "button", "pressed", "COLOR_BUTTON_PRESSED_BACKGROUND")
        capture("button-pressed")
        QTest.mouseRelease(pressed_button, Qt.LeftButton,
                           pos=pressed_button.rect().center())
        for bar, name in ((tabs.tabBar(), "editor_tabs"), (dock_tabs, "dock_tabs")):
            QTest.mouseMove(bar, bar.tabRect(0).center())
            settle()
            tab_fill(bar, 0, name, "hover", "COLOR_TAB_HOVER_BACKGROUND")
            capture(name + "-hover")
        QTest.mouseMove(window, QPoint(window.width() - 6, 6))
        editor.setFocus()
        settle()

        # Stopped-frame cleanup must remove the fill, including when the cursor
        # remains on another line. Restore it for the final overview capture.
        if breakpoint_manager is not None:
            breakpoint_manager.update_pdb_state(False, editor.filename, 10)
            settle()
            line_fill(10, "EDITOR_BACKGROUND", "debug_cleared")
            breakpoint_manager.update_pdb_state(True, editor.filename, 10)
            settle()
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
        if breakpoint_manager is not None:
            pairs.extend([
                ("EDITOR_DEBUGLINE", "EDITOR_BACKGROUND"),
                ("EDITOR_DEBUGLINE", "EDITOR_CURRENTLINE"),
            ])
        distinctions = []
        for first, second in pairs:
            a, b = getattr(SpyderPalette, first, None), getattr(SpyderPalette, second, None)
            ratio = _contrast_ratio(a, b) if a and b else None
            distinctions.append({
                "first": first, "second": second,
                "first_color": a, "second_color": b,
                "contrast": round(ratio, 3) if ratio is not None else None,
                "minimum_visibility_advisory": MIN_SURFACE_CONTRAST,
                "visibility_advisory_passed": ratio is not None and ratio >= MIN_SURFACE_CONTRAST,
                "kind": "fill",
                "passed": bool(a and b and (
                    state_policy == "contrast-borders" or a.lower() != b.lower())),
            })
        if state_policy == "contrast-borders":
            for first, second in BORDER_STATE_PAIRS:
                a, b = getattr(SpyderPalette, first, None), getattr(SpyderPalette, second, None)
                ratio = _contrast_ratio(a, b) if a and b else None
                distinctions.append({
                    "first": first, "second": second, "kind": "border",
                    "first_color": a, "second_color": b,
                    "contrast": round(ratio, 3) if ratio is not None else None,
                    "minimum": MIN_STATE_BORDER_CONTRAST,
                    "passed": ratio is not None and ratio >= MIN_STATE_BORDER_CONTRAST,
                })
        failures = [
            f"{check['widget']}/{check['state']}: expected {check['role']} pixels"
            for check in checks if not check["passed"]
        ] + [
            f"Insufficient {pair['kind']} distinction: {pair['first']}/{pair['second']}"
            for pair in distinctions if not pair["passed"]
        ]
        ui_state_checks = {"checks": checks, "distinctions": distinctions,
                           "ui_state_policy": state_policy,
                           "surface_visibility_basis": "1.15:1 fill distinction QA advisory; not a WCAG requirement",
                           "debug_checks_enabled": breakpoint_manager is not None,
                           "captures": captures, "passed": not failures,
                           "failures": failures}
    png = args.out_dir / f"{args._render_one}--{args._variant}.png"
    pixmap = window.grab()
    if not pixmap.save(str(png), "PNG"):
        raise RuntimeError(f"Could not save {png}")

    # Save the overview and finish all pane-focus checks before opening actual
    # popups. Popup focus must never contaminate the main-window measurements.
    popup_state_checks = None
    if args.ui_states:
        popup_state_checks = _render_popup_states(
            app, window, SpyderPalette, args, settle, state_policy
        )

    palette_values = {}
    for key in dir(SpyderPalette):
        if key.startswith(("COLOR_", "EDITOR_", "SPECIAL_TABS_", "TAB_SELECTED_")):
            value = getattr(SpyderPalette, key)
            if isinstance(value, (str, tuple, list, int, float)):
                palette_values[key] = value
    data = {
        "theme": args._render_one,
        "variant": args._variant,
        "status": "error" if any(
            result and not result["passed"]
            for result in (pane_border_checks, ui_state_checks, popup_state_checks)
        ) else "ok",
        "png": png.name,
        "image_size": [pixmap.width(), pixmap.height()],
        "selected_scheme": scheme,
        "installed_theme_root": str(installed_root),
        "spyder_source": str(Path(spyder.__file__).resolve()),
        "qt_api": qtpy.API_NAME,
        "qt_version": qVersion(),
        "qt_style": app.style().objectName(),
        "isolated_config": True,
        "active_tree_has_focus": tree.hasFocus(),
        "inactive_tree_has_focus": inactive_tree.hasFocus(),
        "resources_loaded": len(THEME_MANAGER._loaded_resource_modules),
        "tree_resource_available": QFile.exists(
            f":/qss_icons/{args._variant}/rc/branch_open.png"
        ),
        "sample_lines": len(SAMPLE.splitlines()),
        "optional_syntax_roles": list(OPTIONAL_PYTHON_SCHEME_KEYS),
        "runtime_syntax_formats_verified": len(OPTIONAL_PYTHON_SCHEME_KEYS),
        "palette": palette_values,
        "warnings": warnings,
    }
    if pane_border_checks is not None:
        data["pane_border_checks"] = pane_border_checks
        if not pane_border_checks["passed"]:
            data["error"] = "; ".join(pane_border_checks["failures"])
    if ui_state_checks is not None:
        data["ui_state_checks"] = ui_state_checks
        if not ui_state_checks["passed"]:
            data["error"] = "; ".join(filter(None, (
                data.get("error"), "; ".join(ui_state_checks["failures"])
            )))
    if popup_state_checks is not None:
        data["popup_state_checks"] = popup_state_checks
        if not popup_state_checks["passed"]:
            data["error"] = "; ".join(filter(None, (
                data.get("error"), "; ".join(popup_state_checks["failures"])
            )))
    args._result_json.write_text(json.dumps(data, indent=2) + "\n")
    # A delayed scroll-flag refresh can otherwise start while parent teardown
    # deletes CodeEditor. Finish it while the document is still alive; these
    # callbacks do not affect any of the captures or checks above.
    from spyder.plugins.editor.panels.scrollflag import ScrollFlagArea

    scroll_flags = editor.panels.get(ScrollFlagArea)
    scroll_flags.update_flags.cancel()
    scroll_flags._update_flags_thread.quit()
    scroll_flags._update_flags_thread.wait()
    window.close()
    return data


def _run_job(args: argparse.Namespace, job: dict) -> dict:
    name = f"{job['theme']}--{job['variant']}"
    log_path = args.out_dir / f"{name}.log"
    started = time.monotonic()
    result = dict(job)
    with tempfile.TemporaryDirectory(prefix="spyder-port-preview-") as temporary:
        work_dir = Path(temporary)
        result_path = work_dir / "result.json"
        command = [
            sys.executable, str(Path(__file__).resolve()),
            "--theme-dir", str(args.theme_dir),
            "--spyder-dir", str(args.spyder_dir),
            "--out-dir", str(args.out_dir),
            "--_render-one", job["theme"],
            "--_variant", job["variant"],
            "--_config-dir", str(work_dir / "config"),
            "--_result-json", str(result_path),
        ]
        if args.pane_borders:
            command.append("--pane-borders")
        if args.ui_states:
            command.append("--ui-states")
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        # Set isolation in the launch environment as well as inside the child.
        environment["SPYDER_CONFDIR"] = str(work_dir / "config")
        try:
            with log_path.open("w") as log:
                completed = subprocess.run(
                    command, cwd=args.spyder_dir, env=environment,
                    stdout=log, stderr=subprocess.STDOUT,
                    timeout=TIMEOUT_SECONDS, check=False,
                )
            result["returncode"] = completed.returncode
            if result_path.is_file():
                result.update(json.loads(result_path.read_text()))
            if completed.returncode != 0 or result.get("status") != "ok":
                result["status"] = "error"
                result.setdefault("error", f"Child exited with status {completed.returncode}; see {log_path.name}")
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"Child exceeded {TIMEOUT_SECONDS} seconds"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["log"] = log_path.name
    return result


def _write_contact_sheets(out_dir: Path, results: list[dict]) -> list[str]:
    """Tile genuine captures; never substitute palette swatches for widgets."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return []
    available = [item for item in results if item.get("png")]
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
    except OSError:
        font = ImageFont.load_default(size=17)
    names = []
    columns, per_page, cell_width, cell_height = 4, 12, 500, 330
    for start in range(0, len(available), per_page):
        group = available[start:start + per_page]
        rows = (len(group) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#242527")
        draw = ImageDraw.Draw(sheet)
        for index, item in enumerate(group):
            x, y = (index % columns) * cell_width, (index // columns) * cell_height
            draw.text((x + 9, y + 7), f"{item['theme']} / {item['variant']}",
                      font=font, fill="#ffffff")
            with Image.open(out_dir / item["png"]) as source:
                thumbnail = source.convert("RGB")
                thumbnail.thumbnail((cell_width - 12, cell_height - 38))
                sheet.paste(thumbnail, (x + 6, y + 33))
        name = f"contact-sheet-{start // per_page + 1:02d}.png"
        sheet.save(out_dir / name)
        names.append(name)
    return names


def main() -> int:
    args = _arguments()
    args.theme_dir = args.theme_dir.expanduser().resolve()
    args.spyder_dir = args.spyder_dir.expanduser().resolve()
    args.out_dir = args.out_dir.expanduser().resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ast.parse(SAMPLE)
    if args._render_one:
        try:
            result = _render_one(args)
            return 0 if result["status"] == "ok" else 1
        except Exception:
            traceback.print_exc()
            return 1

    if not (args.spyder_dir / "spyder" / "__init__.py").is_file():
        raise SystemExit(f"Spyder source directory not found: {args.spyder_dir}")
    jobs = _discover(args.theme_dir, args.themes)
    print(f"Rendering {len(jobs)} variants with at most {WORKERS} isolated children.", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(_run_job, args, job) for job in jobs]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['status']:7} {result['theme']}/{result['variant']}", flush=True)
    results.sort(key=lambda item: (item["theme"], item["variant"]))
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "renderer": str(Path(__file__).resolve()),
        "python": sys.version,
        "theme_dir": str(args.theme_dir),
        "spyder_dir": str(args.spyder_dir),
        "workers": WORKERS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "pane_borders": args.pane_borders,
        "ui_states": args.ui_states,
        "variant_count": len(jobs),
        "success_count": sum(item["status"] == "ok" for item in results),
        "failure_count": sum(item["status"] != "ok" for item in results),
        "results": results,
    }
    manifest["contact_sheets"] = _write_contact_sheets(args.out_dir, results)
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    cards = []
    for item in results:
        title = html.escape(f"{item['theme']} / {item['variant']}")
        overview = item.get("png")
        if overview:
            cards.append(
                f'<article><h2>{title} · {html.escape(item["status"])}</h2>'
                f'<a href="{html.escape(overview)}"><img src="{html.escape(overview)}" '
                f'loading="lazy" alt="{title}"></a><p>'
                + " · ".join(
                    f'<a href="{html.escape(name)}">{html.escape(name.rsplit("--", 1)[-1][:-4])}</a>'
                    for name in (
                        item.get("ui_state_checks", {}).get("captures", [])
                        + item.get("popup_state_checks", {}).get("captures", [])
                    )
                ) + '</p></article>'
            )
    (args.out_dir / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Spyder theme UI review</title>'
        '<style>body{background:#202124;color:#eee;font:15px system-ui;margin:24px}'
        'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(560px,1fr));gap:24px}'
        'img{width:100%;height:auto}h2{font-size:18px}a{color:#9bc9ff}</style>'
        f'<h1>Spyder theme UI review · {manifest["success_count"]}/{len(jobs)} passed</h1>'
        '<p>Real Spyder CodeEditor and Qt styles. Click previews for full-size images.</p>'
        '<p>' + " · ".join(
            f'<a href="{name}">Contact sheet {index + 1}</a>'
            for index, name in enumerate(manifest["contact_sheets"])
        ) + '</p>'
        '<main>' + ''.join(cards) + '</main>\n'
    )
    print(f"Manifest: {manifest_path}", flush=True)
    return 1 if manifest["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
