#!/usr/bin/env python3
"""Verify that Spyder editor surfaces and highlights remain distinguishable.

Only PyYAML is required; ThemeWeaver and a running Spyder are not needed.
The Delta E 1976 limits are this repository's visual separation policy, not
accessibility certification. Contrast ratios use WCAG relative luminance.

Example::

    python .tools/verify_editor_colors.py --out-dir .artifacts/editor-colors/after \
        --baseline .artifacts/editor-colors/baseline.json
"""

import argparse
import html
import itertools
import json
import math
from pathlib import Path
import re
import sys

import yaml


CORE_ROLES = (
    "EDITOR_BACKGROUND", "EDITOR_CURRENTCELL", "EDITOR_CURRENTLINE",
    "COLOR_ACCENT_2",
)
OVERLAY_ROLES = (
    "EDITOR_OCCURRENCE", "COLOR_OCCURRENCE_4", "EDITOR_MATCHED_P",
    "EDITOR_UNMATCHED_P",
)
COLOR_ROLES = CORE_ROLES + OVERLAY_ROLES + ("EDITOR_NORMAL", "COLOR_TEXT_1")
MIN_CORE_DELTA = 6.0
MIN_SELECTION_DELTA = 12.0
MIN_OVERLAY_DELTA = 8.0
MIN_OCCURRENCE_DELTA = 20.0
MIN_OCCURRENCE_BACKGROUND_DELTA = 30.0
MIN_TEXT_CONTRAST = 4.5
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys, including keys hidden by YAML merge syntax."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in result
            except TypeError as error:
                raise ValueError("YAML mapping keys must be scalar") from error
            if duplicate:
                mark = key_node.start_mark
                raise ValueError(
                    f"Duplicate YAML key {key!r} at line {mark.line + 1}"
                )
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def read_yaml(path):
    """Read one YAML mapping with strict duplicate-key detection."""
    try:
        result = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)
    except (yaml.YAMLError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error
    if not isinstance(result, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return result


def rgb(color):
    """Return normalized sRGB channels for an opaque six-digit color."""
    if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
        raise ValueError(f"Expected an opaque #RRGGBB color, got {color!r}")
    return tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))


def linear_rgb(color):
    return tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgb(color)
    )


def luminance(color):
    red, green, blue = linear_rgb(color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first, second):
    a, b = sorted((luminance(first), luminance(second)))
    return (b + 0.05) / (a + 0.05)


def lab(color):
    """Convert sRGB to CIELAB using the standard D65 white point."""
    red, green, blue = linear_rgb(color)
    xyz = (
        (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047,
        0.2126729 * red + 0.7151522 * green + 0.0721750 * blue,
        (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883,
    )

    def transform(value):
        return value ** (1 / 3) if value > 216 / 24389 else value * (24389 / 27) / 116 + 16 / 116

    x, y, z = map(transform, xyz)
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def delta_e(first, second):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab(first), lab(second))))


def resolve_theme(theme_dir):
    """Resolve every semantic reference and return enabled variant colors."""
    theme_dir = Path(theme_dir)
    metadata = read_yaml(theme_dir / "theme.yaml")
    mappings = read_yaml(theme_dir / "mappings.yaml")
    colorsystem = read_yaml(theme_dir / "colorsystem.yaml")
    aliases = mappings.get("color_classes")
    variants = mappings.get("semantic_mappings")
    declared = metadata.get("variants")
    if not isinstance(aliases, dict) or not isinstance(variants, dict) or not isinstance(declared, dict):
        raise ValueError(f"{theme_dir}: missing color_classes, semantic_mappings or variants")
    enabled = {variant for variant, active in declared.items() if active is True}
    if set(variants) != enabled or not enabled:
        raise ValueError(
            f"{theme_dir}: declared variants {sorted(enabled)} differ from "
            f"semantic mappings {sorted(variants)}"
        )

    for alias, class_name in aliases.items():
        if class_name not in colorsystem or not isinstance(colorsystem[class_name], dict):
            raise ValueError(f"{theme_dir}: unresolved color class {alias}: {class_name}")

    def resolve_reference(reference, label):
        if not isinstance(reference, str) or reference.count(".") != 1:
            raise ValueError(f"{theme_dir}: {label}: invalid color reference {reference!r}")
        alias, key = reference.split(".")
        if alias not in aliases or key not in colorsystem[aliases[alias]]:
            raise ValueError(f"{theme_dir}: {label}: unresolved reference {reference!r}")
        color = colorsystem[aliases[alias]][key]
        rgb(color)
        return color.upper()

    result = []
    for variant, mapping in variants.items():
        if not isinstance(mapping, dict):
            raise ValueError(f"{theme_dir}: {variant}: expected semantic role mapping")
        resolved = {}
        for role, value in mapping.items():
            if isinstance(value, list):
                if len(value) != 3 or any(type(flag) is not bool for flag in value[1:]):
                    raise ValueError(f"{theme_dir}: {variant}.{role}: invalid formatted color {value!r}")
                value = value[0]
            if isinstance(value, str):
                resolved[role] = resolve_reference(value, f"{variant}.{role}")
            elif type(value) is not int:
                raise ValueError(f"{theme_dir}: {variant}.{role}: invalid role value {value!r}")
        missing = set(COLOR_ROLES) - resolved.keys()
        if missing:
            raise ValueError(f"{theme_dir}: {variant}: missing editor colors {sorted(missing)}")
        result.append({
            "theme": theme_dir.name,
            "variant": variant,
            "colors": {role: resolved[role] for role in COLOR_ROLES},
        })
    return result


def evaluate_variant(entry):
    """Check core pair differences, overlays, bracket states and text contrast."""
    colors = entry["colors"]
    checks = []

    def add(kind, first, second, minimum):
        measure = delta_e if kind == "delta_e76" else contrast_ratio
        value = measure(colors[first], colors[second])
        checks.append({
            "kind": kind, "first": first, "second": second,
            "value": round(value, 6), "minimum": minimum,
            "passed": value + 1e-9 >= minimum,
        })

    for first, second in itertools.combinations(CORE_ROLES, 2):
        minimum = MIN_SELECTION_DELTA if "COLOR_ACCENT_2" in (first, second) else MIN_CORE_DELTA
        add("delta_e76", first, second, minimum)
    for overlay in OVERLAY_ROLES:
        for surface in CORE_ROLES:
            if overlay == "EDITOR_OCCURRENCE":
                minimum = (MIN_OCCURRENCE_BACKGROUND_DELTA
                           if surface == "EDITOR_BACKGROUND" else MIN_OCCURRENCE_DELTA)
            else:
                minimum = MIN_OVERLAY_DELTA
            add("delta_e76", overlay, surface, minimum)
    for first, second in itertools.combinations(OVERLAY_ROLES, 2):
        # Occurrences and find results indicate the same class of text match.
        if (first, second) != ("EDITOR_OCCURRENCE", "COLOR_OCCURRENCE_4"):
            add("delta_e76", first, second, MIN_OVERLAY_DELTA)
    for surface in CORE_ROLES[:3] + OVERLAY_ROLES:
        add("contrast", "EDITOR_NORMAL", surface, MIN_TEXT_CONTRAST)
    add("contrast", "COLOR_TEXT_1", "COLOR_ACCENT_2", MIN_TEXT_CONTRAST)
    return {
        **entry, "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "failure_count": sum(not check["passed"] for check in checks),
    }


def load_baseline(path):
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else data["variants"]
    result = {}
    for entry in entries:
        key = entry["theme"], entry["variant"]
        if key in result:
            raise ValueError(f"{path}: duplicate baseline variant {key}")
        result[key] = entry
    return result


def add_baseline_changes(entry, baseline):
    previous = baseline.get((entry["theme"], entry["variant"]))
    entry["changes"] = []
    if previous is None:
        return
    for role, color in entry["colors"].items():
        before = previous["colors"].get(role)
        if before is not None and color.upper() != before.upper():
            entry["changes"].append({"role": role, "before": before, "after": color})
    previous_checks = {
        (check["kind"], check["first"], check["second"]): check
        for check in evaluate_variant(previous)["checks"]
    } if set(COLOR_ROLES) <= previous["colors"].keys() else {}
    for check in entry["checks"]:
        old = previous_checks.get((check["kind"], check["first"], check["second"]))
        if old is not None:
            check["baseline_value"] = old["value"]
            check["baseline_passed"] = old["passed"]


def write_html(report, path):
    escape = html.escape
    rows = []
    for entry in report["variants"]:
        colors = entry["colors"]
        cells = []
        for role in COLOR_ROLES:
            foreground = colors["COLOR_TEXT_1"] if role == "COLOR_ACCENT_2" else colors["EDITOR_NORMAL"]
            if role in ("EDITOR_NORMAL", "COLOR_TEXT_1"):
                foreground = colors["EDITOR_BACKGROUND"]
            cells.append(
                f'<td style="background:{colors[role]};color:{foreground}">'
                f'<span>Abc 123</span><small>{colors[role]}</small></td>'
            )
        failures = [
            f'{check["first"]} / {check["second"]}: {check["value"]:.2f} &lt; {check["minimum"]:g}'
            for check in entry["checks"] if not check["passed"]
        ]
        changes = [
            f'{change["role"]}: {change["before"]} → {change["after"]}'
            for change in entry.get("changes", [])
        ]
        details = "<br>".join(escape(line) for line in changes)
        if failures:
            # Failure labels are role names and numeric values produced above.
            details += '<div class="fail">' + "<br>".join(failures) + "</div>"
        identity = escape(f'{entry["theme"]} / {entry["variant"]}')
        status = "PASS" if entry["passed"] else f'{entry["failure_count"]} FAIL'
        rows.append(
            f'<tr><th>{identity}<small>{status}</small></th>{"".join(cells)}</tr>'
            + (f'<tr><td class="details" colspan="11">{details}</td></tr>' if details else "")
        )
    errors = "".join(f'<li>{escape(error)}</li>' for error in report["errors"])
    headers = "".join(f'<th>{escape(role)}</th>' for role in COLOR_ROLES)
    path.write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Spyder editor color audit</title><style>'
        'body{font:14px system-ui;margin:24px;background:#fafafa;color:#222}'
        'table{border-collapse:collapse;table-layout:fixed;min-width:1300px;width:100%}'
        'th,td{border:1px solid #aaa;padding:10px;overflow-wrap:anywhere}'
        'th{font-size:11px}thead th{position:sticky;top:0;background:#eee}'
        'td{text-align:center;font:14px monospace}small{display:block;font-size:11px;margin-top:5px}'
        '.details{text-align:left;font:11px monospace;padding:5px 12px}.fail{color:#a00}'
        '.scroll{overflow:auto}</style><h1>Spyder editor color audit</h1>'
        f'<p>{report["summary"]["variants"]} variants; '
        f'{report["summary"]["failed_variants"]} failed variants; '
        f'{report["summary"]["failed_checks"]} failed checks.</p>'
        '<p>Internal visual separation policy (CIELAB ΔE76): core surfaces ≥6, '
        'selection versus core ≥12, occurrence versus editor background ≥30, '
        'occurrence versus cell, line and selection backgrounds ≥20, '
        'other overlays versus core and bracket states ≥8. '
        'Normal text and selected text contrast ≥4.5:1. Occurrence and find may share a color. '
        'These swatches are palette checks; actual Qt rendering requires separate verification.</p>'
        f'<ul class="fail">{errors}</ul><div class="scroll"><table><thead><tr>'
        f'<th>Theme / variant</th>{headers}</tr></thead><tbody>{"".join(rows)}</tbody>'
        '</table></div></html>\n', encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--theme-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--themes", nargs="+", help="Only inspect these theme directory names")
    parser.add_argument("--out-dir", type=Path, help="Write report.json and index.html")
    parser.add_argument("--baseline", type=Path, help="Earlier report.json to compare colors and checks")
    parser.add_argument("--quiet", action="store_true", help="Print only the final summary and errors")
    args = parser.parse_args(argv)
    report = {
        "schema_version": 1,
        "thresholds": {
            "core_delta_e76": MIN_CORE_DELTA, "selection_delta_e76": MIN_SELECTION_DELTA,
            "overlay_delta_e76": MIN_OVERLAY_DELTA,
            "occurrence_delta_e76": MIN_OCCURRENCE_DELTA,
            "occurrence_background_delta_e76": MIN_OCCURRENCE_BACKGROUND_DELTA,
            "text_contrast": MIN_TEXT_CONTRAST,
        },
        "variants": [], "errors": [],
    }
    try:
        baseline = load_baseline(args.baseline)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    paths = sorted(path.parent for path in args.theme_dir.glob("*/theme.yaml"))
    if args.themes:
        missing = set(args.themes) - {path.name for path in paths}
        report["errors"].extend(f"Unknown theme: {name}" for name in sorted(missing))
        paths = [path for path in paths if path.name in args.themes]
    if not paths:
        report["errors"].append(f"No themes found under {args.theme_dir}")
    for theme_dir in paths:
        try:
            entries = resolve_theme(theme_dir)
            for raw in entries:
                entry = evaluate_variant(raw)
                add_baseline_changes(entry, baseline)
                report["variants"].append(entry)
        except (OSError, ValueError, KeyError, TypeError) as error:
            report["errors"].append(str(error))
    report["summary"] = {
        "themes": len({entry["theme"] for entry in report["variants"]}),
        "variants": len(report["variants"]),
        "checks": sum(len(entry["checks"]) for entry in report["variants"]),
        "failed_variants": sum(not entry["passed"] for entry in report["variants"]),
        "failed_checks": sum(entry["failure_count"] for entry in report["variants"]),
        "changed_variants": sum(bool(entry["changes"]) for entry in report["variants"]),
        "errors": len(report["errors"]),
    }
    report["passed"] = not report["errors"] and not report["summary"]["failed_checks"]
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        write_html(report, args.out_dir / "index.html")
    if not args.quiet:
        for entry in report["variants"]:
            status = "PASS" if entry["passed"] else f'FAIL ({entry["failure_count"]})'
            print(f'{entry["theme"]}/{entry["variant"]}: {status}')
            for check in entry["checks"]:
                if not check["passed"]:
                    print(f'  {check["kind"]}: {check["first"]} / {check["second"]}: '
                          f'{check["value"]:.3f} < {check["minimum"]:g}')
    for error in report["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    summary = report["summary"]
    print(f'{"PASS" if report["passed"] else "FAIL"}: {summary["themes"]} themes / '
          f'{summary["variants"]} variants; {summary["checks"]} checks; '
          f'{summary["failed_checks"]} failures; {summary["errors"]} errors')
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
