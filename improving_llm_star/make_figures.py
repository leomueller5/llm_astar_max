"""
Figures for the LLM-A*-WW report
================================

Creates all figures of the report from the result files of the notebook `LLM_AStar_WW.ipynb`
(folder improving_llm_star/results/); no search is run here:

  fig1_example_paths.png      maps with expanded cells, paths and waypoints: A* vs. LLM-A* vs. LLM-A*-WW
  fig6_failure_cases.png      the same for the worst failure case of each type (two examples)
  fig4_per_sample_or.png      per-sample operation ratio of LLM-A* vs. LLM-A*-WW
  fig5_pseudocode.png         pseudocode of LLM-A*-WW and of the line-of-sight validation

Run the notebook first, then (from the repository root):

    python improving_llm_star/make_figures.py

The figures are written to improving_llm_star/figures/ (PNG, 300 dpi).
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                               # render to files, no window
import matplotlib.pyplot as plt                     # noqa: E402
import numpy as np                                  # noqa: E402
from matplotlib.lines import Line2D                 # noqa: E402
from matplotlib.patches import Patch                # noqa: E402

HERE = Path(__file__).resolve().parent              # .../improving_llm_star
RESULTS = HERE / "results"
FIGURES = HERE / "figures"

# ---------------------------------------------------------------------------------------------------
# Colours: one fixed colour per method, used in every figure.
# ---------------------------------------------------------------------------------------------------
C_WW = "#2a78d6"            # LLM-A*-WW (blue)
C_LLM = "#eb6834"           # LLM-A* (orange)
C_ASTAR = "#6b6a65"         # A* and other baselines (neutral grey)
C_OBST = "#2b2b2b"          # barriers
C_TEXT = "#0b0b0b"
C_MUTED = "#52514e"
C_GRID = "#e4e3df"

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": C_MUTED, "axes.labelcolor": C_TEXT, "xtick.color": C_MUTED,
    "ytick.color": C_MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.facecolor": "white",
})



# ===================================================================================================
# Figure 1: example maps
# ===================================================================================================
def draw_map(ax, ex, method, colour, title):
    """Draw barriers, expanded cells, path, start/goal and waypoints of one saved search.

    ex is one entry of example_searches.json (written by the notebook), method "A*", "LLM-A*" or
    "LLM-A*-WW".
    """
    width, height = ex["width"], ex["height"]
    search = ex[method]
    waypoints_used = search.get("waypoints_used", [])
    waypoints_dropped = search.get("waypoints_dropped", []) if method == "LLM-A*-WW" else []

    # Expanded cells (light tint of the method colour) and barriers (dark).
    grid = np.zeros((height, width, 4))
    tint = matplotlib.colors.to_rgba(colour, 0.28)
    for x, y in search["closed"]:
        if 0 <= x < width and 0 <= y < height:
            grid[y, x] = tint
    for x, y in ex["obstacles"]:
        grid[y, x] = matplotlib.colors.to_rgba(C_OBST)
    ax.imshow(grid, origin="lower", interpolation="nearest",
              extent=(-0.5, width - 0.5, -0.5, height - 0.5))

    # Path.
    path = search["path"]
    ax.plot([p[0] for p in path], [p[1] for p in path], color=colour, lw=2, solid_capstyle="round",
            zorder=3)

    # Waypoints: used ones filled, discarded ones as grey crosses.
    if waypoints_dropped:
        ax.scatter(*zip(*waypoints_dropped), marker="x", s=36, color=C_MUTED, lw=1.5, zorder=4)
    if waypoints_used:
        ax.scatter(*zip(*waypoints_used), marker="D", s=34, color=colour, edgecolor="white", lw=1,
                   zorder=5)

    # Start and goal.
    ax.scatter(*ex["start"], marker="o", s=60, color=C_TEXT, edgecolor="white", lw=1.2, zorder=6)
    ax.scatter(*ex["goal"], marker="*", s=130, color=C_TEXT, edgecolor="white", lw=1, zorder=6)

    ax.set_title(title, loc="left", color=C_TEXT)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def figure_example_paths(examples):
    fig, axes = plt.subplots(len(examples), 3, figsize=(12, 3.0 * len(examples)))
    for row_axes, (sample_id, ex) in zip(axes, examples.items()):
        n_astar = ex["A*"]["operation"]

        def label(name):
            n = ex[name]["operation"]
            return f"{name}: {n} expanded ({100 * n / n_astar:.0f} % of A*)"

        draw_map(row_axes[0], ex, "A*", C_ASTAR, f"Map {sample_id}  |  A*: {n_astar} expanded")
        draw_map(row_axes[1], ex, "LLM-A*", C_LLM, label("LLM-A*"))
        draw_map(row_axes[2], ex, "LLM-A*-WW", C_WW, label("LLM-A*-WW"))

    add_map_legend(fig)
    fig.suptitle("Example searches (Few-Shot prompt, same LLM answer for LLM-A* and LLM-A*-WW)",
                 x=0.01, ha="left", fontsize=11, color=C_TEXT)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_example_paths.png")
    plt.close(fig)
    return list(examples)


def add_map_legend(fig):
    legend = [
        Patch(facecolor=C_OBST, label="barrier"),
        Patch(facecolor=matplotlib.colors.to_rgba(C_MUTED, 0.3), label="expanded cells"),
        Line2D([], [], color=C_MUTED, lw=2, label="path"),
        Line2D([], [], marker="o", color=C_TEXT, lw=0, markersize=7, label="start"),
        Line2D([], [], marker="*", color=C_TEXT, lw=0, markersize=11, label="goal"),
        Line2D([], [], marker="D", color=C_MUTED, lw=0, markersize=6, label="waypoint used"),
        Line2D([], [], marker="x", color=C_MUTED, lw=0, markersize=7, mew=1.5,
               label="waypoint discarded by LLM-A*-WW"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, -0.03))


def path_length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def figure_failure_cases(failures):
    """Worst case of each failure type (chosen in the notebook, section 7)."""
    fig, axes = plt.subplots(len(failures), 3, figsize=(12, 3.25 * len(failures)))
    for k, (row_axes, (sample_id, ex)) in enumerate(zip(axes, failures.items())):
        n_astar, len_astar = ex["A*"]["operation"], path_length(ex["A*"]["path"])

        def label(name):
            n, length = ex[name]["operation"], path_length(ex[name]["path"])
            return f"{name}: {n} expanded ({100 * n / n_astar:.0f} %), path {100 * length / len_astar:.0f} %"

        draw_map(row_axes[0], ex, "A*", C_ASTAR,
                 f"({chr(97 + k)}) {ex['kind']}\nMap {sample_id}  |  A*: {n_astar} expanded")
        draw_map(row_axes[1], ex, "LLM-A*", C_LLM, "\n" + label("LLM-A*"))
        draw_map(row_axes[2], ex, "LLM-A*-WW", C_WW, "\n" + label("LLM-A*-WW"))
    add_map_legend(fig)
    fig.suptitle("Failure cases of LLM-A*-WW (Few-Shot prompt; worst sample of each type, "
                 "percentages relative to A*)", x=0.01, ha="left", fontsize=11, color=C_TEXT)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig6_failure_cases.png")
    plt.close(fig)
    return list(failures)


# ===================================================================================================
# Figure 4: per-sample comparison
# ===================================================================================================
def figure_per_sample(rows):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True, sharey=True)
    for ax, (pt, name) in zip(axes, [("standard", "Few-Shot"), ("cot", "CoT"), ("repe", "RePE")]):
        a = np.array([r["A*"][0] for r in rows], dtype=float)
        llm = 100 * np.array([r[f"LLM-A*|{pt}"][0] for r in rows]) / a
        ww = 100 * np.array([r[f"LLM-A*-WW|{pt}"][0] for r in rows]) / a
        ax.scatter(llm, ww, s=9, color=C_WW, alpha=0.35, lw=0, zorder=2)
        lims = (3, 1500)
        ax.plot(lims, lims, color=C_MUTED, lw=1, ls="--", zorder=1)
        ax.axvline(100, color=C_GRID, lw=1, zorder=0)
        ax.axhline(100, color=C_GRID, lw=1, zorder=0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ticks = [5, 10, 25, 50, 100, 200, 500, 1000]
        ax.set_xticks(ticks, [str(t) for t in ticks])
        ax.set_yticks(ticks, [str(t) for t in ticks])
        ax.minorticks_off()
        better = np.mean(ww < llm) * 100
        worse = np.mean(ww > llm) * 100
        ax.set_title(name, loc="left")
        ax.text(0.03, 0.97, f"WW better: {better:.1f} %\nWW worse: {worse:.1f} %\nequal: "
                f"{100 - better - worse:.1f} %", transform=ax.transAxes, va="top", fontsize=8,
                color=C_TEXT)
        ax.text(lims[1] * 0.9, lims[1] * 0.75, "equal", ha="right", va="top", fontsize=8,
                color=C_MUTED, rotation=45)
        ax.set_xlabel("LLM-A*: operation ratio (% of A*)")
    axes[0].set_ylabel("LLM-A*-WW: operation ratio (% of A*)")
    fig.suptitle("Per-sample comparison (1000 samples): points below the diagonal = LLM-A*-WW "
                 "expands fewer cells", x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig4_per_sample_or.png")
    plt.close(fig)


# ===================================================================================================
# Figure 5: pseudocode
# ===================================================================================================
# Each line: (line number or "", indentation level, text, comment, differs from LLM-A*?)
# Text uses matplotlib "mathtext": $...$ is typeset like LaTeX math.
ALGORITHM_MAIN = [
    ("", 0, r"$\mathbf{Input}$: start $s_0$, goal $s_g$, map $M$, LLM, switch radius $r$", "", False),
    ("", 0, r"$\mathbf{Output}$: path from $s_0$ to $s_g$", "", False),
    ("", 0, r"$\mathbf{Priority}$: $f(s) = g(s) + h(s) + \alpha_t\,\Vert s - t\Vert + (1-\alpha_t)\,h(s)$",
     r"$h$: Euclidean distance to $s_g$", True),
    ("1", 0, r"$W \leftarrow$ LLM(prompt($s_0, s_g, M$))", "waypoints, same prompt as LLM-A*", False),
    ("2", 0, r"$W \leftarrow \{\, w \in W$ : $w$ is free and inside $M \,\}$", "", False),
    ("3", 0, r"$(T, \alpha) \leftarrow$ LOSVALIDATE$(s_0, W, s_g)$", "Algorithm 2", True),
    ("4", 0, r"$i \leftarrow 1$;   $t \leftarrow T[1]$", "current target", False),
    ("5", 0, r"$g(s_0) \leftarrow 0$;   OPEN $\leftarrow \{s_0\}$;   CLOSED $\leftarrow \emptyset$", "", False),
    ("6", 0, r"$\mathbf{while}$ OPEN $\neq \emptyset$ $\mathbf{do}$", "", False),
    ("7", 1, r"$s \leftarrow$ state in OPEN with the smallest $f(s)$;   move $s$ to CLOSED", "", False),
    ("8", 1, r"$\mathbf{if}$ $s = s_g$ $\mathbf{then}$ $\mathbf{return}$ path via parent pointers", "", False),
    ("9", 1, r"$\mathbf{for\ each}$ neighbour $n$ of $s$ $\mathbf{do}$", "", False),
    ("10", 2, r"$\mathbf{if}$ $t \neq s_g$ $\mathbf{and}$ ( $n = t$ $\mathbf{or}$ $\Vert s - t\Vert \leq r$ ) $\mathbf{then}$",
     "target reached (early switch)", True),
    ("11", 3, r"$i \leftarrow i + 1$;   $t \leftarrow T[i]$;   recompute $f$ for all states in OPEN", "", False),
    ("12", 2, r"$\mathbf{if}$ $n \in$ CLOSED $\mathbf{then}$ $\mathbf{continue}$", "", False),
    ("13", 2, r"$\mathbf{if}$ $g(s) + c(s, n) < g(n)$ $\mathbf{then}$", r"$c = \infty$ if a barrier is hit", False),
    ("14", 3, r"$g(n) \leftarrow g(s) + c(s, n)$;   parent$(n) \leftarrow s$;   insert $n$ into OPEN", "", False),
    ("15", 0, r"$\mathbf{return}$ failure", "", False),
]

ALGORITHM_LOS = [
    ("", 0, r"$\mathbf{Input}$: start $s_0$, LLM waypoints $w_1, \ldots, w_k$, goal $s_g$", "", False),
    ("", 0, r"$\mathbf{Output}$: target list $T$ and weights $\alpha$", "", False),
    ("1", 0, r"$Q \leftarrow [\,s_0, w_1, \ldots, w_k, s_g\,]$;   $T \leftarrow [\,s_0\,]$;   $i \leftarrow 0$", "", True),
    ("2", 0, r"$\mathbf{while}$ $i < |Q| - 1$ $\mathbf{do}$", "", True),
    ("3", 1, r"$j \leftarrow$ largest index $> i$ such that segment $Q[i]\,Q[j]$ hits no barrier",
     "farthest visible point", True),
    ("4", 1, r"$\mathbf{if}$ no such $j$ exists $\mathbf{or}$ $j = |Q| - 1$ $\mathbf{then}$ $\mathbf{break}$",
     "chain broken / goal visible", True),
    ("5", 1, r"append $Q[j]$ to $T$;   $i \leftarrow j$", "skipped points are detours", True),
    ("6", 0, r"append $s_g$ to $T$", "", True),
    ("7", 0, r"$\mathbf{return}$ $T$ with $\alpha_t = 1$ for all $t \in T$",
     r"removed waypoints: $\alpha = 0$", True),
]

C_HIGHLIGHT = "#e3eefb"     # light blue band behind lines that differ from LLM-A*


def draw_algorithm(ax, top, title, lines, width):
    """Draw one algorithm box starting at y = top (in inches, y grows downwards). Returns the bottom."""
    line_h, indent = 0.27, 0.30
    x_num, x_text, x_comment = 0.12, 0.50, width - 2.55
    y = top
    ax.plot([0, width], [y, y], color=C_TEXT, lw=1.2)                       # top rule
    ax.text(0.05, y + 0.20, title, fontsize=10.5, va="center", color=C_TEXT)
    y += 0.40
    ax.plot([0, width], [y, y], color=C_TEXT, lw=0.6)                       # rule below the title
    y += 0.10
    for number, level, text, comment, new in lines:
        yc = y + line_h / 2
        if new:
            ax.add_patch(plt.Rectangle((0, y), width, line_h, color=C_HIGHLIGHT, lw=0, zorder=0))
        if number:
            ax.text(x_num + 0.18, yc, number, fontsize=8, ha="right", va="center", color=C_MUTED)
        x = x_text + level * indent if number else 0.05
        for lv in range(level):                                             # indentation guides
            ax.plot([x_text + lv * indent + 0.06] * 2, [y, y + line_h], color=C_GRID, lw=0.8, zorder=1)
        ax.text(x, yc, text, fontsize=9.5, va="center", color=C_TEXT, zorder=2)
        if comment:
            ax.text(x_comment, yc, r"$\triangleright$ " + comment, fontsize=8.5, va="center",
                    color=C_MUTED, style="italic", zorder=2)
        y += line_h
    y += 0.08
    ax.plot([0, width], [y, y], color=C_TEXT, lw=1.2)                       # bottom rule
    return y


def figure_pseudocode():
    width = 9.0
    n_lines = len(ALGORITHM_MAIN) + len(ALGORITHM_LOS)
    height = n_lines * 0.27 + 2 * 0.62 + 0.45 + 0.35
    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-0.05, width + 0.05)
    ax.set_ylim(height, 0)                                                  # y axis points down
    ax.axis("off")
    with plt.rc_context({"mathtext.fontset": "dejavuserif", "font.family": "DejaVu Serif"}):
        bottom = draw_algorithm(ax, 0.05, r"$\mathbf{Algorithm\ 1}$  LLM-A*-WW (LLM-A* with weighted waypoints)",
                                ALGORITHM_MAIN, width)
        bottom = draw_algorithm(ax, bottom + 0.45,
                                r"$\mathbf{Algorithm\ 2}$  LOSVALIDATE: line-of-sight validation of the waypoints",
                                ALGORITHM_LOS, width)
        ax.add_patch(plt.Rectangle((0, bottom + 0.12), 0.25, 0.16, color=C_HIGHLIGHT, lw=0))
        ax.text(0.33, bottom + 0.20, "differs from LLM-A* (in LLM-A*: all waypoints are kept, "
                r"$\alpha_t = 1$, and the target switches only when $n = t$)",
                fontsize=8.5, va="center", color=C_MUTED)
        fig.savefig(FIGURES / "fig5_pseudocode.png")
    plt.close(fig)


# ===================================================================================================
# Main
# ===================================================================================================
def main():
    FIGURES.mkdir(exist_ok=True)
    with open(RESULTS / "per_sample_results_ww.json", encoding="utf-8") as f:
        rows = json.load(f)
    with open(RESULTS / "example_searches.json", encoding="utf-8") as f:
        example_data = json.load(f)

    examples = figure_example_paths(example_data)
    print(f"fig1_example_paths.png   (samples {', '.join(examples)})")
    with open(RESULTS / "failure_searches.json", encoding="utf-8") as f:
        failures = figure_failure_cases(json.load(f))
    print(f"fig6_failure_cases.png   (samples {', '.join(failures)})")
    figure_per_sample(rows)
    print("fig4_per_sample_or.png")
    figure_pseudocode()
    print("fig5_pseudocode.png")
    print(f"Saved to {FIGURES}")


if __name__ == "__main__":
    main()
