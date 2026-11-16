#!/usr/bin/env python3
"""Verify editor state colors with genuine Spyder CodeEditor widgets.

Run with the Python used by Spyder. To inspect an exported wheel without
installing it, extract the wheel and prepend that directory to PYTHONPATH::

    PYTHONPATH=/tmp/theme-wheel python .tools/verify_editor_rendering.py \
        --out-dir .artifacts/editor-state-review

Every variant uses a fresh process and temporary Spyder configuration. Source
YAML, the imported palette, runtime editor colors and rendered pixels must
agree. No test colors or stylesheet overrides are introduced. Screenshots show
the actual cell/line/selection, occurrence/find and matched/unmatched brace
states; pixel boxes avoid glyphs where possible and otherwise check the modal
background. This checks rendering, not an accessibility certification.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import html
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
WORKERS = 2
TIMEOUT = 90
ROLES = (
    "EDITOR_BACKGROUND", "EDITOR_CURRENTCELL", "EDITOR_CURRENTLINE",
    "EDITOR_OCCURRENCE", "EDITOR_MATCHED_P", "EDITOR_UNMATCHED_P",
    "COLOR_ACCENT_2", "COLOR_TEXT_1", "COLOR_OCCURRENCE_4", "EDITOR_NORMAL",
)
SAMPLE = "\n".join((
    "# %% Active cell",
    "# Current cell, current line and dragged text remain visible together.",
    "value = 1",
    "cell_selection = '                                        '",
    "line_selection = '                                        '",
    "needle = value + value",
    "matched = ()",
    "unmatched = (",
    "",
    "# %% Inactive cell",
    "inactive = value + 2",
    "find_target = 'find_me   find_me'",
    "# This cell keeps the ordinary editor background.",
    "",
))


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme-dir", type=Path, default=ROOT)
    parser.add_argument("--spyder-dir", type=Path, default=ROOT.parent / "spyder6_ok97465")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--themes", nargs="+")
    parser.add_argument("--_theme", help=argparse.SUPPRESS)
    parser.add_argument("--_variant", choices=("dark", "light"), help=argparse.SUPPRESS)
    parser.add_argument("--_config", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_result", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def discover(args):
    import yaml

    names = args.themes or sorted(path.name for path in args.theme_dir.iterdir()
                                 if (path / "theme.yaml").is_file())
    jobs = []
    for name in dict.fromkeys(names):
        if name in (".", "..") or Path(name).name != name:
            raise ValueError(f"Invalid theme ID: {name!r}")
        metadata = yaml.safe_load((args.theme_dir / name / "theme.yaml").read_text())
        jobs.extend({"theme": name, "variant": variant}
                    for variant in ("dark", "light")
                    if metadata["variants"].get(variant) is True)
    if not jobs:
        raise ValueError("No theme variants found")
    return jobs


def source_palette(args):
    import yaml

    directory = args.theme_dir / args._theme
    mapping = yaml.safe_load((directory / "mappings.yaml").read_text())
    colors = yaml.safe_load((directory / "colorsystem.yaml").read_text())

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, str) and "." in value and not value.startswith("#"):
            group, key = value.split(".", 1)
            return colors[mapping["color_classes"].get(group, group)][key]
        return value

    return {role: resolve(mapping["semantic_mappings"][args._variant][role])
            for role in ROLES}


def render(args):
    config = args._config.resolve()
    config.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "SPYDER_CONFDIR": str(config), "SPYDER_USE_DEV_CONFIG_DIR": "false",
        "XDG_CONFIG_HOME": str(config / "xdg-config"),
        "XDG_CACHE_HOME": str(config / "cache"),
        "MPLCONFIGDIR": str(config / "matplotlib"),
        "IPYTHONDIR": str(config / "ipython"),
        "JUPYTER_CONFIG_DIR": str(config / "jupyter"),
        "QT_SCALE_FACTOR": "1", "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    os.environ.pop("SPYDER_PYTEST", None)
    os.environ.pop("SPYDER_SAFE_MODE", None)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.spyder_dir))
    sys.argv = [str(Path(__file__).resolve())]

    from spyder.config.manager import CONF

    scheme = f"spyder_themes.{args._theme}/{args._variant}"
    CONF.set("appearance", "selected", scheme)
    CONF.set("appearance", "ui_theme", args._variant)

    import qtpy
    from qtpy.QtCore import Qt, qVersion
    from qtpy.QtGui import QFontDatabase, QTextCursor
    from qtpy.QtTest import QTest
    from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    app = QApplication([])
    app.setStyle("Fusion")
    from spyder.utils.theme_manager import THEME_MANAGER
    from spyder.utils.palette import SpyderPalette
    from spyder.utils.stylesheet import APP_STYLESHEET
    from spyder.plugins.editor.widgets.codeeditor.codeeditor import CodeEditor

    THEME_MANAGER.load_pending_resources()
    app.setStyleSheet(str(APP_STYLESHEET))
    module = importlib.import_module(f"spyder_themes.{args._theme}")
    installed = getattr(module, f"SpyderPalette{args._variant.title()}")
    source = source_palette(args)
    checks = []

    def compare(name, expected, observed):
        def normalize(value):
            if isinstance(value, (tuple, list)):
                return [normalize(item) for item in value]
            return value.lower() if isinstance(value, str) else value

        checks.append({"check": name, "expected": expected, "observed": observed,
                       "passed": normalize(expected) == normalize(observed)})

    for role, expected in source.items():
        compare(f"source_to_export.{role}", expected, getattr(installed, role))
        compare(f"export_to_runtime.{role}", getattr(installed, role), getattr(SpyderPalette, role))

    window = QWidget()
    window.resize(1000, 530)
    layout = QVBoxLayout(window)
    title = QLabel()
    layout.addWidget(title)
    editor = CodeEditor(window)
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setPointSize(13)
    editor.setup_editor(
        language="Python", linenumbers=True, markers=False, folding=False,
        scrollflagarea=False, edge_line=False, indent_guides=False,
        show_blanks=False, automatic_completions=False, completions_hint=False,
        hover_hints=False, code_snippets=False, show_class_func_dropdown=False,
        highlight_current_cell=True, highlight_current_line=True,
        occurrence_highlighting=False, font=font,
        filename=str(config / "editor-state-preview.py"), color_scheme=scheme,
    )
    layout.addWidget(editor)
    editor.set_text(SAMPLE)
    editor.highlighter.rehighlight()
    window.show()
    window.activateWindow()
    editor.setFocus(Qt.OtherFocusReason)

    def settle():
        app.processEvents()
        QTest.qWait(60)
        app.processEvents()

    def cursor(line, column=0):
        result = QTextCursor(editor.document().findBlockByNumber(line))
        result.setPosition(result.position() + column)
        return result

    def move(line, column=0):
        editor.setTextCursor(cursor(line, column))
        editor.highlight_current_cell()
        editor.highlight_current_line()
        settle()

    def pixel_check(state, role, rectangle):
        image = editor.viewport().grab().toImage()
        scale = image.devicePixelRatio()
        x, y, width, height = rectangle
        left, top = max(0, int(x * scale)), max(0, int(y * scale))
        right = min(image.width(), int((x + width) * scale))
        bottom = min(image.height(), int((y + height) * scale))
        colors = Counter(image.pixelColor(px, py).name().lower()
                         for py in range(top, bottom) for px in range(left, right))
        expected = getattr(SpyderPalette, role).lower()
        observed, count = colors.most_common(1)[0] if colors else (None, 0)
        total = sum(colors.values())
        checks.append({
            "check": f"pixels.{state}", "role": role,
            "expected": expected, "observed": observed,
            "expected_fraction": round(colors[expected] / total, 3) if total else 0,
            "modal_fraction": round(count / total, 3) if total else 0,
            "rectangle": list(rectangle),
            "passed": observed == expected and count / max(1, total) >= 0.4,
        })

    def line_pixels(line, role, state):
        rect = editor.cursorRect(cursor(line))
        pixel_check(state, role, (editor.viewport().width() * .76,
                                 rect.y() + 2, editor.viewport().width() * .18,
                                 max(2, rect.height() - 4)))

    def text_pixels(line, start, end, role, state):
        first = editor.cursorRect(cursor(line, start))
        last = editor.cursorRect(cursor(line, end))
        pixel_check(state, role, (first.x(), first.y() + 1,
                                 max(2, last.x() - first.x()), first.height() - 2))

    captures = []

    def capture(state, caption):
        title.setText(f"{args._theme} / {args._variant} · {caption}")
        settle()
        name = f"{args._theme}--{args._variant}--{state}.png"
        window.grab().save(str(args.out_dir / name))
        captures.append(name)

    move(4, 25)
    for role, attr in (
        ("EDITOR_CURRENTLINE", "currentline_color"),
        ("EDITOR_CURRENTCELL", "currentcell_color"),
        ("EDITOR_OCCURRENCE", "occurrence_color"),
        ("EDITOR_MATCHED_P", "matched_p_color"),
        ("EDITOR_UNMATCHED_P", "unmatched_p_color"),
        ("COLOR_OCCURRENCE_4", "found_results_color"),
    ):
        compare(f"runtime_editor.{role}", getattr(SpyderPalette, role),
                getattr(editor, attr).name())
    compare("current_cell_enabled", True, editor.highlight_current_cell_enabled)
    compare("cell_separators_detected", True, editor.has_cell_separators)
    line_pixels(10, "EDITOR_BACKGROUND", "ordinary_background")
    line_pixels(2, "EDITOR_CURRENTCELL", "active_cell")
    line_pixels(4, "EDITOR_CURRENTLINE", "current_line")

    # A real multiline selection ends in the current line. Its first line is
    # inside the same active cell, so both overlapping backgrounds are checked.
    selection = cursor(3, 23)
    selection.setPosition(cursor(4, 43).position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(selection)
    settle()
    text_pixels(3, 25, 39, "COLOR_ACCENT_2", "selection_over_cell")
    text_pixels(4, 25, 39, "COLOR_ACCENT_2", "selection_over_current_line")
    line_pixels(4, "EDITOR_CURRENTLINE", "current_line_beside_selection")
    capture("selection", "ordinary background · active cell · current line · dragged selection")

    move(5, SAMPLE.splitlines()[5].index("value") + 1)
    editor.mark_occurrences()
    editor.highlight_found_results("find_me")
    settle()
    text_pixels(2, 0, 5, "EDITOR_OCCURRENCE", "occurrence_over_cell")
    start = SAMPLE.splitlines()[5].index("value")
    text_pixels(5, start, start + 5, "EDITOR_OCCURRENCE", "occurrence_over_current_line")
    start = SAMPLE.splitlines()[10].index("value")
    text_pixels(10, start, start + 5, "EDITOR_OCCURRENCE", "occurrence_over_background")
    start = SAMPLE.splitlines()[11].index("find_me")
    text_pixels(11, start, start + 7, "COLOR_OCCURRENCE_4", "find_over_background")
    capture("search", "current word occurrences · search results")

    editor.clear_occurrences()
    editor.clear_found_results()
    matched_column = SAMPLE.splitlines()[6].index("(")
    matched_position = cursor(6, matched_column).position()
    # Spyder infers comment/string context from foreground-color equality.
    # Some native palettes intentionally share punctuation and comment colors.
    # An empty pair still exercises the genuine matched decoration without
    # conflating that separate syntax-context limitation with fill rendering.
    brace_context = {
        "opening_bracket_reported_as_comment": editor.in_comment(position=matched_position),
        "opening_bracket_reported_as_string": editor.in_string(position=matched_position),
        "sample": "matched = ()",
    }
    move(6, matched_column + 1)
    editor.cursor_position_changed()
    settle()
    text_pixels(6, matched_column, matched_column + 1, "EDITOR_MATCHED_P", "matched_bracket")
    capture("matched", "matched parentheses over the current line")

    unmatched_column = SAMPLE.splitlines()[7].index("(")
    move(7, unmatched_column + 1)
    editor.cursor_position_changed()
    settle()
    text_pixels(7, unmatched_column, unmatched_column + 1, "EDITOR_UNMATCHED_P", "unmatched_bracket")
    capture("unmatched", "unmatched parenthesis over the current line")

    from spyder.plugins.editor.panels.scrollflag import ScrollFlagArea

    flags = editor.panels.get(ScrollFlagArea)
    flags.update_flags.cancel()
    flags._update_flags_thread.quit()
    flags._update_flags_thread.wait()
    result = {
        "theme": args._theme, "variant": args._variant,
        "status": "ok" if all(check["passed"] for check in checks) else "error",
        "checks": checks, "check_count": len(checks),
        "failed_checks": [check["check"] for check in checks if not check["passed"]],
        "captures": captures, "png": captures[0],
        "source_palette": source, "isolated_config": True,
        "brace_context": brace_context,
        "warnings": ([
            "Spyder infers bracket context from foreground colors. This palette "
            "shares bracket and comment/string colors, which can prevent matching "
            "across other syntax tokens. The matched-state capture uses an empty pair."
        ] if brace_context["opening_bracket_reported_as_comment"]
             or brace_context["opening_bracket_reported_as_string"] else []),
        "installed_theme_root": str(Path(module.__file__).resolve().parent),
        "qt_api": qtpy.API_NAME, "qt_version": qVersion(),
        "qt_style": app.style().objectName(),
    }
    args._result.write_text(json.dumps(result, indent=2) + "\n")
    window.close()
    return result


def run_job(args, job):
    result = dict(job)
    name = f"{job['theme']}--{job['variant']}"
    started = time.monotonic()
    log = args.out_dir / f"{name}.log"
    with tempfile.TemporaryDirectory(prefix="spyder-editor-states-") as temporary:
        directory = Path(temporary)
        output = directory / "result.json"
        command = [sys.executable, str(Path(__file__).resolve()),
                   "--theme-dir", str(args.theme_dir), "--spyder-dir", str(args.spyder_dir),
                   "--out-dir", str(args.out_dir), "--_theme", job["theme"],
                   "--_variant", job["variant"], "--_config", str(directory / "config"),
                   "--_result", str(output)]
        environment = os.environ.copy()
        environment["SPYDER_CONFDIR"] = str(directory / "config")
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            with log.open("w") as stream:
                completed = subprocess.run(command, cwd=args.spyder_dir, env=environment,
                                           stdout=stream, stderr=subprocess.STDOUT,
                                           timeout=TIMEOUT, check=False)
            if output.is_file():
                result.update(json.loads(output.read_text()))
            if completed.returncode or result.get("status") != "ok":
                result["status"] = "error"
                result.setdefault("error", f"Child exit {completed.returncode}; see {log.name}")
        except subprocess.TimeoutExpired:
            result.update(status="timeout", error=f"Exceeded {TIMEOUT} seconds")
    result["log"] = log.name
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def write_gallery(args, results):
    from PIL import Image, ImageDraw, ImageFont

    available = [item for item in results if item.get("png")]
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
    except OSError:
        font = ImageFont.load_default()
    sheets = []
    for start in range(0, len(available), 12):
        group = available[start:start + 12]
        sheet = Image.new("RGB", (1800, ((len(group) + 2) // 3) * 350), "#252628")
        draw = ImageDraw.Draw(sheet)
        for index, item in enumerate(group):
            x, y = index % 3 * 600, index // 3 * 350
            draw.text((x + 8, y + 6), f"{item['theme']} / {item['variant']}",
                      font=font, fill="white")
            with Image.open(args.out_dir / item["png"]) as image:
                thumbnail = image.convert("RGB")
                thumbnail.thumbnail((590, 310))
                sheet.paste(thumbnail, (x + 5, y + 32))
        name = f"contact-sheet-{start // 12 + 1:02d}.png"
        sheet.save(args.out_dir / name)
        sheets.append(name)
    cards = []
    for item in results:
        label = html.escape(f"{item['theme']} / {item['variant']} · {item['status']}")
        links = " · ".join(f'<a href="{html.escape(name)}">{html.escape(name.rsplit("--", 1)[-1][:-4])}</a>'
                           for name in item.get("captures", []))
        picture = (f'<a href="{item["png"]}"><img src="{item["png"]}" loading="lazy"></a>'
                   if item.get("png") else "")
        cards.append(f"<article><h2>{label}</h2>{picture}<p>{links}</p></article>")
    (args.out_dir / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Spyder editor state review</title>'
        '<style>body{background:#202124;color:#eee;font:15px system-ui;margin:24px}'
        'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(540px,1fr));gap:24px}'
        'img{width:100%;height:auto}h2{font-size:18px}a{color:#9bc9ff}</style>'
        '<h1>Spyder editor state review</h1>'
        '<p>Real CodeEditor widgets, isolated configuration, original theme styles.</p>'
        '<main>' + "".join(cards) + '</main>\n')
    return sheets


def main():
    args = arguments()
    for key in ("theme_dir", "spyder_dir", "out_dir"):
        setattr(args, key, getattr(args, key).expanduser().resolve())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args._theme:
        try:
            return 0 if render(args)["status"] == "ok" else 1
        except Exception:
            traceback.print_exc()
            return 1
    jobs = discover(args)
    print(f"Checking {len(jobs)} variants with {WORKERS} isolated children.", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(run_job, args, job) for job in jobs]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['status']:7} {result['theme']}/{result['variant']} "
                  + ", ".join(result.get("failed_checks", [])), flush=True)
    results.sort(key=lambda item: (item["theme"], item["variant"]))
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "variant_count": len(jobs),
        "success_count": sum(item["status"] == "ok" for item in results),
        "failure_count": sum(item["status"] != "ok" for item in results),
        "check_count": sum(item.get("check_count", 0) for item in results),
        "contact_sheets": write_gallery(args, results), "results": results,
    }
    path = args.out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest: {path}", flush=True)
    return 1 if manifest["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
