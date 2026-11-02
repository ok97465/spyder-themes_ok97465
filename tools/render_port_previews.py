#!/usr/bin/env python3
"""Render installed theme ports with real Spyder/Qt widgets.

Run this with the Python environment that launches Spyder, after exporting and
installing the theme bundle. Source YAML selects the ports/variants to render;
all displayed colors and resources come from the installed theme package.

Example::

    python tools/render_port_previews.py --out-dir /tmp/spyder-port-previews
    python tools/render_port_previews.py --out-dir /tmp/tokyo-preview \
        --themes tokyonight tokyo-night-altsynt

No live Spyder application, projects, consoles, or personal configuration are
opened. Each variant runs in a fresh child process with temporary configuration
and cache directories. At most two children run concurrently, each with a
120-second timeout. PNGs, per-variant logs, and manifest.json are written only
inside the requested output directory.
"""

from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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
TIMEOUT_SECONDS = 120
WINDOW_SIZE = (1180, 900)

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
    from qtpy.QtCore import QFile, QSize, Qt, qVersion
    from qtpy.QtGui import QFontDatabase
    from qtpy.QtWidgets import (
        QApplication, QLabel, QMainWindow, QSplitter, QStyle, QTabBar,
        QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
    )

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
    window.resize(*WINDOW_SIZE)

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
    status.showMessage("Ready · isolated preview · six nested bracket levels")
    status.addPermanentWidget(QLabel("Python   |   Spaces: 4   |   UTF-8  "))

    window.show()
    window.activateWindow()
    # One tree has an active selection, the second an inactive selection. Both
    # use the real stylesheet paths; their backgrounds are never painted here.
    tree.setFocus()
    editor.verticalScrollBar().setValue(0)
    for _ in range(6):
        app.processEvents()
        time.sleep(0.025)
    png = args.out_dir / f"{args._render_one}--{args._variant}.png"
    pixmap = window.grab()
    if not pixmap.save(str(png), "PNG"):
        raise RuntimeError(f"Could not save {png}")

    palette_values = {}
    for key in dir(SpyderPalette):
        if key.startswith(("COLOR_", "EDITOR_", "SPECIAL_TABS_", "TAB_SELECTED_")):
            value = getattr(SpyderPalette, key)
            if isinstance(value, (str, tuple, list, int, float)):
                palette_values[key] = value
    data = {
        "theme": args._render_one,
        "variant": args._variant,
        "status": "ok",
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
    args._result_json.write_text(json.dumps(data, indent=2) + "\n")
    window.close()
    app.processEvents()
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
                result["error"] = f"Child exited with status {completed.returncode}; see {log_path.name}"
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"Child exceeded {TIMEOUT_SECONDS} seconds"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["log"] = log_path.name
    return result


def main() -> int:
    args = _arguments()
    args.theme_dir = args.theme_dir.expanduser().resolve()
    args.spyder_dir = args.spyder_dir.expanduser().resolve()
    args.out_dir = args.out_dir.expanduser().resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ast.parse(SAMPLE)
    if args._render_one:
        try:
            _render_one(args)
            return 0
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
        "variant_count": len(jobs),
        "success_count": sum(item["status"] == "ok" for item in results),
        "failure_count": sum(item["status"] != "ok" for item in results),
        "results": results,
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest: {manifest_path}", flush=True)
    return 1 if manifest["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
