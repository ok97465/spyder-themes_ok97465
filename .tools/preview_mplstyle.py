#!/usr/bin/env python3
"""Preview the Matplotlib style from a terminal or Spyder (F5).

Examples::

    python .tools/preview_mplstyle.py
    MPLBACKEND=Agg python .tools/preview_mplstyle.py --save-dir .artifacts/mplstyle --no-show

Except for plot-specific needs documented below, colors come from the style.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator, LogLocator


DEFAULT_STYLE = Path(__file__).resolve().parents[1] / "mplstyle/vscode-modern-dark.mplstyle"


def line_scatter_hist_bar(rng, theme_name="VS Code Modern Dark"):
    """Exercise the default color cycle, legends, markers and filled patches."""
    fig, axs = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    fig.suptitle(f"{theme_name} | Lines, scatter, histograms and bars")
    x = np.linspace(0, 2 * np.pi, 180)
    ax = axs[0, 0]
    for i in range(6):
        ax.plot(x, np.sin(x + i * 0.45) + i * 0.35, label=f"Series {i + 1}")
    ax.set(title="Six default cycle colors", xlabel="Time (s)", ylabel="Signal")
    ax.legend(ncols=2, title="Line legend")

    ax = axs[0, 1]
    for i, marker in enumerate(("o", "s", "^")):
        points = rng.normal(size=(65, 2)) * (0.55, 0.45) + (i * 1.2, i * 0.7)
        ax.scatter(*points.T, s=27, marker=marker, alpha=0.8, label=f"Group {i + 1}")
    ax.set(title="Categorical scatter", xlabel="Feature A", ylabel="Feature B")
    ax.legend(title="Marker + color")

    ax = axs[1, 0]
    bins = np.linspace(-3.5, 4, 32)
    for i, mean in enumerate((0.0, 0.9)):
        ax.hist(rng.normal(mean, 1, 700), bins=bins, alpha=0.55, label=f"Sample {i + 1}")
    ax.set(title="Overlapping histograms, alpha=0.55", xlabel="Value", ylabel="Count")
    ax.legend()

    ax = axs[1, 1]
    positions = np.arange(4)
    for i in range(3):
        ax.bar(positions + (i - 1) * 0.24, rng.uniform(2, 6, 4), width=0.24, label=f"Run {i + 1}")
    ax.set(title="Grouped bars", xlabel="Category", ylabel="Score", xticks=positions)
    ax.set_xticklabels(("A", "B", "C", "D"))
    ax.set_ylim(0, 8)
    ax.legend(ncols=3, loc="upper center")
    return "01_lines_scatter_histogram_bars", fig


def error_log_heatmap_contour(rng, theme_name="VS Code Modern Dark"):
    """Exercise uncertainty, log ticks, scalar images and colorbar text."""
    fig, axs = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    fig.suptitle(f"{theme_name} | Uncertainty, log axes and colorbars")
    ax = axs[0, 0]
    x = np.linspace(0, 6, 28)
    y = np.exp(-x / 4) * np.sin(x)
    error = 0.12 + 0.03 * np.cos(x)
    line = ax.errorbar(x, y, yerr=error, fmt="o-", markersize=4, label="Measurement")
    # Match the band to its associated line; alpha tests compositing on dark axes.
    ax.fill_between(x, y - error, y + error, color=line.lines[0].get_color(), alpha=0.2, label="Uncertainty")
    ax.set(title="Error bars and translucent band", xlabel="Time (s)", ylabel="Response")
    ax.legend()

    ax = axs[0, 1]
    x = np.geomspace(0.1, 100, 160)
    ax.loglog(x, x**0.65, label=r"$x^{0.65}$")
    ax.loglog(x, 2 * x**0.35, "--", label=r"$2x^{0.35}$")
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10)))
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10)))
    ax.grid(True, which="minor", alpha=0.22, linewidth=0.45)
    ax.set(title="Log scales and minor grid", xlabel="Frequency (Hz)", ylabel="Power")
    ax.legend()

    ax = axs[1, 0]
    # No cmap argument: this verifies the style's image.cmap setting (viridis).
    image = ax.imshow(rng.normal(size=(14, 20)), aspect="auto")
    ax.set(title="Heatmap: default sequential colormap", xlabel="Column", ylabel="Row")
    fig.colorbar(image, ax=ax, label="Intensity")

    ax = axs[1, 1]
    grid = np.linspace(-3, 3, 70)
    xx, yy = np.meshgrid(grid, grid)
    zz = np.sin(xx) * np.cos(yy)
    # Diverging quantities need an explicit diverging cmap; image.cmap is sequential.
    contour = ax.contourf(xx, yy, zz, levels=np.linspace(-1, 1, 15), cmap="coolwarm")
    ax.set(title="Diverging contour and colorbar", xlabel="X position", ylabel="Y position")
    fig.colorbar(contour, ax=ax, label="Signed deviation")
    return "02_errorbars_log_heatmap_contour", fig


def box_violin_pie_annotation(rng, theme_name="VS Code Modern Dark"):
    """Exercise statistical artists, outliers, pie labels and math text."""
    fig, axs = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    fig.suptitle(f"{theme_name} | Distributions, labels and annotations")
    groups = [np.r_[rng.normal(i * 0.45, 0.6, 90), 3.0 + i * 0.3] for i in range(3)]
    ax = axs[0, 0]
    ax.boxplot(groups, tick_labels=("A", "B", "C"), showmeans=True)
    ax.set(title="Boxplot, whiskers, means and outliers", xlabel="Group", ylabel="Value")

    ax = axs[0, 1]
    violin = ax.violinplot(groups, showmeans=True, showmedians=True)
    # Matplotlib has no violin-specific rcParams. Set each body's fill/edge and
    # collection lines explicitly; these do not consistently inherit a dark style.
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for body, color in zip(violin["bodies"], cycle):
        body.set(facecolor=color, edgecolor=plt.rcParams["text.color"], alpha=0.65)
    for key in ("cbars", "cmins", "cmaxes", "cmeans", "cmedians"):
        violin[key].set(color=plt.rcParams["text.color"], linewidth=1.1)
    ax.set(title="Violin bodies with explicit collection colors", xlabel="Group", ylabel="Value")
    ax.set_xticks([1, 2, 3], ["A", "B", "C"])

    ax = axs[1, 0]
    wedges, _, percentages = ax.pie([38, 27, 21, 14], labels=["Python", "Data", "Plots", "Other"], autopct="%1.0f%%", startangle=90)
    # Pie labels sit on the dark figure, but percentages sit inside bright wedges.
    # No separate autopct rcParam exists, so give only the percentages dark text.
    for wedge, percentage in zip(wedges, percentages):
        choices = (plt.rcParams["figure.facecolor"], plt.rcParams["text.color"])
        percentage.set_color(max(choices, key=lambda c: contrast(c, wedge.get_facecolor())))
    ax.set_title("Pie wedges, labels and percentages")

    ax = axs[1, 1]
    x = np.linspace(0, 2 * np.pi, 160)
    ax.plot(x, np.sin(x), label=r"$y=\sin(x)$")
    ax.axhline(0, color=plt.rcParams["axes.edgecolor"], linewidth=0.8)
    # Arrow colors are per-annotation properties, so choose the style text color.
    ax.annotate(r"Peak: $\sin(\pi/2)=1$", xy=(np.pi / 2, 1), xytext=(2.6, 1.3),
                arrowprops={"arrowstyle": "->", "color": plt.rcParams["text.color"]})
    ax.text(0.04, 0.08, r"$\int_0^\pi \sin(x)\,dx=2$", transform=ax.transAxes)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.set(title="Annotation and math text", xlabel=r"Phase $\theta$ (rad)", ylabel="Amplitude", ylim=(-1.5, 1.7))
    ax.legend(loc="lower right")
    return "03_boxplot_violin_pie_annotation", fig


def contrast(first, second):
    """Return relative luminance contrast for opaque sRGB colors."""
    def luminance(color):
        rgb = np.array(mcolors.to_rgb(color))
        linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        return float(linear @ [0.2126, 0.7152, 0.0722])

    a, b = sorted((luminance(first), luminance(second)))
    return (b + 0.05) / (a + 0.05)


def build_galleries(style_path):
    """Apply one standalone style and build the same seeded sample figures."""
    style_path = Path(style_path).expanduser().resolve()
    plt.style.use(["default", str(style_path)])
    first_line = style_path.read_text(encoding="utf-8").splitlines()[0]
    theme_name = first_line.removeprefix("# ").removesuffix(" companion for Matplotlib.")
    rng = np.random.default_rng(97465)
    return [
        line_scatter_hist_bar(rng, theme_name),
        error_log_heatmap_contour(rng, theme_name),
        box_violin_pie_annotation(rng, theme_name),
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE, help="Path to an .mplstyle file")
    parser.add_argument("--save-dir", type=Path, help="Save all figures as both PNG and SVG")
    parser.add_argument("--no-show", action="store_true", help="Render/save without opening plot windows")
    # Spyder/IPython can supply its own launch arguments when executing a file.
    args, _unknown = parser.parse_known_args(argv)
    style_path = args.style.expanduser().resolve()
    if not style_path.is_file():
        parser.error(f"Style file not found: {style_path}")
    galleries = build_galleries(style_path)
    if args.save_dir is not None:
        output_dir = args.save_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, figure in galleries:
            for extension in ("png", "svg"):
                figure.savefig(output_dir / f"{name}.{extension}")
        print(f"Saved {len(galleries)} figures (PNG + SVG): {output_dir}")
    print(f"Applied Matplotlib style: {style_path}")
    if args.no_show:
        for _, figure in galleries:
            plt.close(figure)
    else:
        plt.show()


if __name__ == "__main__":
    main()
