#!/usr/bin/env python3
"""Validate and render every companion Matplotlib style, without opening a GUI.

Run from any directory; optionally select styles with --styles <file stem> ...
The output includes three PNG/SVG galleries per style, contact sheets and JSON.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"text": 7.0, "legend_text": 7.0, "tick": 4.5, "cycle": 3.0, "edge": 3.0}
TYPOGRAPHY = {"font.size": 11, "axes.labelsize": 11, "axes.titlesize": 12,
              "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 10}


def luminance(color):
    channels = np.array(colors.to_rgb(color))
    linear = np.where(channels <= 0.04045, channels / 12.92,
                      ((channels + 0.055) / 1.055) ** 2.4)
    return float(linear @ [0.2126, 0.7152, 0.0722])


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


class CaptureWarnings(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def check_settings():
    rc = mpl.rcParams
    figure, axes, legend = [rc[key] for key in
                            ("figure.facecolor", "axes.facecolor", "legend.facecolor")]
    assert colors.to_rgba(figure) != colors.to_rgba(axes), "Figure and axes must differ"
    assert max(luminance(figure), luminance(axes)) < 0.15, "Background is not dark"
    assert all(colors.to_rgba(c)[3] == 1 for c in (figure, axes, legend)), "Transparent surface"
    assert rc["legend.framealpha"] == 1 and rc["legend.frameon"], "Legend must be opaque"
    assert rc["savefig.facecolor"] == "auto" and not rc["savefig.transparent"], "Save background"
    for key, expected in TYPOGRAPHY.items():
        assert rc[key] == expected, f"Unexpected typography: {key}={rc[key]}"
    cycle = rc["axes.prop_cycle"].by_key()["color"]
    assert len(cycle) >= 6 and len(set(cycle)) == len(cycle), "Need at least six distinct colors"
    for value in [*cycle, rc["lines.color"], rc["patch.edgecolor"], rc["scatter.edgecolors"]]:
        assert colors.is_color_like(value), f"Invalid rendering color: {value}"
    ratios = {"text": min(contrast(rc[k], axes) for k in ("text.color", "axes.labelcolor")),
              "legend_text": contrast(rc["legend.labelcolor"], legend),
              "tick": min(contrast(rc[k], axes) for k in ("xtick.color", "ytick.color")),
              "cycle": min(contrast(color, axes) for color in cycle),
              "edge": contrast(rc["axes.edgecolor"], axes)}
    for key, minimum in LIMITS.items():
        assert ratios[key] >= minimum, f"{key}: {ratios[key]:.3f} < {minimum}"
    return {"contrast": {k: round(v, 3) for k, v in ratios.items()},
            "figure": colors.to_hex(figure), "axes": colors.to_hex(axes),
            "cycle": cycle, "typography": {k: rc[k] for k in TYPOGRAPHY}}


def check_saved(png, svg, settings):
    expected = tuple(round(c * 255) for c in colors.to_rgb(settings["figure"]))
    with Image.open(png) as image:
        image = image.convert("RGBA")
        assert image.width >= 600 and image.height >= 400, "Image is too small"
        assert image.getpixel((0, 0)) == (*expected, 255), "Saved figure background changed"
        data = np.asarray(image)
        assert data[:, :, 3].min() == 255, "PNG has transparent pixels"
        axes_color = np.array([round(c * 255) for c in colors.to_rgb(settings["axes"])])
        assert np.count_nonzero(np.all(data[:, :, :3] == axes_color, axis=2)) > 1000, "Axes missing"
        size = list(image.size)
    ET.parse(svg)
    vector = svg.read_text(encoding="utf-8")
    for key in ("figure", "axes"):
        assert f"fill: {settings[key]}" in vector, f"SVG {key} background changed"
    return {"png": str(png), "svg": str(svg), "pixels": size,
            "png_bytes": png.stat().st_size, "svg_bytes": svg.stat().st_size}


def validate_style(path, helper, output):
    result = {"style": path.name, "status": "failed", "outputs": []}
    handler = CaptureWarnings()
    logger = logging.getLogger("matplotlib")
    logger.addHandler(handler)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            params = mpl.rc_params_from_file(path, use_default_template=False, fail_on_error=True)
            with plt.style.context(["default", str(path)]):
                result.update(check_settings())
                result["parameter_count"] = len(params)
                directory = output / path.stem
                directory.mkdir(parents=True, exist_ok=True)
                galleries = helper.build_galleries(path)
                assert len(galleries) == 3, "Expected three gallery figures"
                for name, figure in galleries:
                    for axis in figure.axes:
                        legend = axis.get_legend()
                        if legend is not None:
                            assert legend.get_frame().get_alpha() == 1, "Rendered legend is transparent"
                    png, svg = [directory / f"{name}.{ext}" for ext in ("png", "svg")]
                    figure.savefig(png)
                    figure.savefig(svg)
                    result["outputs"].append(check_saved(png, svg, result))
                    plt.close(figure)
            assert not handler.messages, "Matplotlib warnings: " + "; ".join(handler.messages)
        result["status"] = "passed"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        plt.close("all")
        logger.removeHandler(handler)
    return result


def contact_sheets(results, output):
    passed = [r for r in results if r["status"] == "passed"]
    font = ImageFont.truetype(str(Path(mpl.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 23)
    sheets = []
    for start in range(0, len(passed), 9):
        batch = passed[start:start + 9]
        sheet = Image.new("RGB", (3 * 720, ((len(batch) + 2) // 3) * 550), "#181818")
        draw = ImageDraw.Draw(sheet)
        for index, result in enumerate(batch):
            x, y = (index % 3) * 720, (index // 3) * 550
            draw.text((x + 14, y + 10), result["style"].removesuffix(".mplstyle"), font=font, fill="#DDDDDD")
            with Image.open(result["outputs"][0]["png"]) as original:
                thumb = original.convert("RGB")
                thumb.thumbnail((700, 500), Image.Resampling.LANCZOS)
                sheet.paste(thumb, (x + 10 + (700 - thumb.width) // 2, y + 45))
        path = output / f"contact-sheet-{start // 9 + 1:02d}.png"
        sheet.save(path)
        sheets.append(str(path))
    return sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".artifacts/mplstyle-gallery")
    parser.add_argument("--styles", nargs="+", help="Style file stems, without .mplstyle")
    args = parser.parse_args()
    available = {p.stem: p for p in sorted((ROOT / "mplstyle").glob("*.mplstyle"))}
    names = [Path(name).stem for name in args.styles] if args.styles else list(available)
    unknown = set(names) - available.keys()
    if unknown or not names:
        parser.error(f"Unknown or empty style selection: {sorted(unknown)}")
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("mplstyle_preview", ROOT / ".tools/preview_mplstyle.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    results = []
    for name in names:
        result = validate_style(available[name], helper, output)
        results.append(result)
        print(f"{result['status'].upper()}: {name}" + (f" — {result['error']}" if "error" in result else ""))
    report = {"matplotlib_version": mpl.__version__, "contrast_minimums": LIMITS,
              "styles": results, "contact_sheets": contact_sheets(results, output)}
    report["passed"] = sum(r["status"] == "passed" for r in results)
    report["failed"] = len(results) - report["passed"]
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {report['passed']}/{len(results)} styles: {output / 'validation.json'}")
    return bool(report["failed"])


if __name__ == "__main__":
    raise SystemExit(main())
