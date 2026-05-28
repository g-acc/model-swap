#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""
Parse smoke test output and render a paired bar chart per step:
  upper bar — timing: time_to_first_byte | generation  (left/bottom x-axis, seconds)
  lower bar — throughput                               (top x-axis, bytes/s)

Color encodes cache action; shade encodes segment (dark = TTFB, light = generation).
Colors use the Wong colorblind-safe palette.

Usage:
  ./test_cache_smoke.sh 2>&1 | uv run benchmarks/plot_run.py --title "LRU policy"
  uv run benchmarks/plot_run.py benchmarks/cache_run.txt
  uv run benchmarks/plot_run.py benchmarks/cache_run.txt -o benchmarks/cache_run.png
"""

import re
import sys
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ── parsing ───────────────────────────────────────────────────────────────────

LABEL_RE = re.compile(r"^===\s+(.+?)\s+===")
TIMING_RE = re.compile(
    r"\[http (\d+)"
    r"\s*\|\s*tcp_connect=([0-9.]+)s"
    r"\s+time_to_first_byte=([0-9.]+)s"
    r"\s+generation=([0-9.]+)s"
    r"\s+total=([0-9.]+)s"
    r"\s*\|\s*throughput=~([0-9.]+)\s*bytes/s\]"
)
ACTION_KEYWORDS = ["load_from_store", "load_from_cache", "already_loaded", "rejected"]


def _infer_action(label: str) -> str:
    lower = label.lower()
    for kw in ACTION_KEYWORDS:
        if kw in lower:
            return kw
    return "unknown"


def parse(text: str) -> list[dict]:
    steps, current_label = [], None
    for line in text.splitlines():
        m = LABEL_RE.match(line)
        if m:
            current_label = m.group(1)
            continue
        m = TIMING_RE.search(line)
        if m and current_label:
            steps.append({
                "label":       current_label,
                "action":      _infer_action(current_label),
                "http":        int(m.group(1)),
                "tcp_connect": float(m.group(2)),
                "ttfb":        float(m.group(3)),
                "generation":  float(m.group(4)),
                "total":       float(m.group(5)),
                "throughput":  float(m.group(6)),
            })
            current_label = None
    return steps


# ── color scheme ─────────────────────────────────────────────────────────────
# TTFB bars use blues and yellows.
# Generation bars use reds and blacks.
# Throughput is neutral gray.

ACTION_COLORS: dict[str, tuple[str, str]] = {
    #                   ttfb (blue/yellow)    gen (red/black)
    "load_from_store": ("#0072B2",            "#C0392B"),  # blue       / red
    "load_from_cache": ("#E69F00",            "#1A1A2E"),  # amber      / near-black
    "already_loaded":  ("#56B4E9",            "#922B21"),  # sky blue   / dark red
    "rejected":        ("#F0E442",            "#717D7E"),  # yellow     / gray
    "unknown":         ("#AAAAAA",            "#555555"),
}

TPUT_COLOR = "#666666"  # neutral gray for throughput bars

# y-offsets within each step row (inverted axis: negative = visually higher)
TIME_OFFSET = -0.22   # timing bar sits above the step label
TPUT_OFFSET = +0.22   # throughput bar sits below
BAR_H = 0.32


# ── plotting ──────────────────────────────────────────────────────────────────

def _short_label(label: str, max_len: int = 45) -> str:
    label = re.sub(r"\s*->\s*expect:.*", "", label).strip()
    return label if len(label) <= max_len else label[: max_len - 1] + "…"


def plot(steps: list[dict], output_path: str, title: str | None = None) -> None:
    n = len(steps)
    fig, ax = plt.subplots(figsize=(12, max(5, n * 1.5 + 2.5)))
    ax2 = ax.twiny()  # secondary x-axis (top) shares the y-axis; used for throughput

    max_total = max(s["total"] for s in steps)
    max_tput  = max(s["throughput"] for s in steps)
    ax.set_xlim(0, max_total * 1.4)
    ax2.set_xlim(0, max_tput * 1.4)
    time_pad = max_total * 0.02
    tput_pad  = max_tput  * 0.02

    for i, s in enumerate(steps):
        c_ttfb, c_gen = ACTION_COLORS.get(s["action"], ACTION_COLORS["unknown"])

        # ── timing bar (bottom x-axis) ────────────────────────────────────────
        ax.barh(i + TIME_OFFSET, s["ttfb"],       left=0,         color=c_ttfb, height=BAR_H, zorder=3)
        ax.barh(i + TIME_OFFSET, s["generation"], left=s["ttfb"], color=c_gen,  height=BAR_H, zorder=3)
        ax.text(s["total"] + time_pad, i + TIME_OFFSET,
                f"{s['total']:.3f}s", va="center", fontsize=7.5, color="#222222")

        # ── throughput bar (top x-axis) ───────────────────────────────────────
        ax2.barh(i + TPUT_OFFSET, s["throughput"], color=TPUT_COLOR, height=BAR_H, alpha=0.65, zorder=3)
        ax2.text(s["throughput"] + tput_pad, i + TPUT_OFFSET,
                 f"{s['throughput']:.0f} B/s", va="center", fontsize=7.5, color="#444444")

    # ── axes ──────────────────────────────────────────────────────────────────
    ax.set_ylim(-0.5, n - 0.5)
    ax.invert_yaxis()
    ax.set_yticks(range(n))
    ax.set_yticklabels([_short_label(s["label"]) for s in steps], fontsize=9)
    ax.set_xlabel("Time (seconds)", fontsize=10, labelpad=8)
    ax2.set_xlabel("Throughput (bytes / s)", fontsize=10, labelpad=8)
    ax.set_title(title or "Smoke Test — Timing Breakdown", fontsize=12, pad=22)
    ax.grid(axis="x", linestyle="--", alpha=0.3, zorder=0)
    ax.spines["right"].set_visible(False)

    # light dividers between steps
    for i in range(n - 1):
        ax.axhline(i + 0.5, color="#DDDDDD", linewidth=0.8, zorder=1)

    # ── legend ────────────────────────────────────────────────────────────────
    seen_actions = [a for a in ACTION_KEYWORDS if any(s["action"] == a for s in steps)]

    handles = []
    for a in seen_actions:
        c, _ = ACTION_COLORS[a]
        handles.append(mpatches.Patch(color=c, label=f"TTFB — {a}"))
    for a in seen_actions:
        _, c = ACTION_COLORS[a]
        handles.append(mpatches.Patch(color=c, label=f"generation — {a}"))
    handles.append(mpatches.Patch(color=TPUT_COLOR, alpha=0.65, label="throughput (top axis)"))

    ax.legend(handles=handles, loc="lower right", fontsize=8,
              framealpha=0.92, handlelength=1.2, borderpad=0.9)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"Saved → {output_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("input", nargs="?", help="Smoke test output file (default: stdin)")
    p.add_argument("-o", "--output", help="Output PNG path")
    p.add_argument("--title", help="Chart title")
    args = p.parse_args()

    if args.input:
        text = Path(args.input).read_text()
        default_out = str(Path(args.input).with_suffix(".png"))
    else:
        text = sys.stdin.read()
        default_out = "benchmarks/smoke_bench.png"

    output_path = args.output or default_out
    steps = parse(text)

    if not steps:
        print(
            "No timing data found. Pipe smoke test output here or pass a saved file.\n"
            "  Example: ./test_cache_smoke.sh 2>&1 | uv run benchmarks/plot_run.py",
            file=sys.stderr,
        )
        sys.exit(1)

    plot(steps, output_path, title=args.title)


if __name__ == "__main__":
    main()
