#!/usr/bin/env python3
"""Annex A charts for the v3-PQ spec (draft v1.6).

Data sources: PoC_by_pieces/piece-03, -04, -07, -09 RESULTS.md, econ/econ.py (cost model)
and davinci-zkvm BENCHMARK.md (v2 production numbers).
Run: ~/.cache/chartenv/bin/python annex_charts.py   (writes ../annex-*.svg)
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
import numpy as np

GREEN, GREEN_S = "#d5e8d4", "#82b366"
BLUE, BLUE_S = "#dae8fc", "#6c8ebf"
YELLOW, YELLOW_S = "#fff2cc", "#d6b656"
ORANGE, ORANGE_S = "#ffe6cc", "#d79b00"
RED, RED_S = "#f8cecc", "#b85450"
GREY, GREY_S = "#f5f5f5", "#999999"

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.edgecolor": "#999999",
    "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none",
})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"../{name}", format="svg")
    plt.close(fig)
    print(name)

def label(ax, bars, texts, dy):
    for b, t in zip(bars, texts):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, t, ha="center", fontsize=8)

# 1. Throughput: v3 STARK stage (piece-07), v3 with wrap (piece-09), v2 with wrap (v2 benchmark, nf=16)
ks = ["64", "128", "256"]
stark, wrapped, v2 = [1.94, 2.27, 2.47], [1.68, 2.10, 2.39], [2.12, 2.80, 3.33]
x, w = np.arange(3), 0.27
fig, ax = plt.subplots(figsize=(7.0, 3.5))
b1 = ax.bar(x - w, stark, w, color=BLUE, edgecolor=BLUE_S, label="v3, STARK stage only")
b2 = ax.bar(x, wrapped, w, color=GREEN, edgecolor=GREEN_S, label="v3, wrapped proof (on-chain ready)")
b3 = ax.bar(x + w, v2, w, color=GREY, edgecolor=GREY_S, label="v2 production, wrapped, 16 fields")
for b, v in ((b1, stark), (b2, wrapped), (b3, v2)):
    label(ax, b, [f"{t:.2f}" for t in v], 0.05)
ax.set_xticks(x, ks)
ax.set_xlabel("batch size (ballots per batch proof)")
ax.set_ylabel("votes / second / GPU")
ax.set_ylim(0, 4.2)
ax.set_title("Sequencer throughput on one RTX 5090 (measured)")
ax.legend(fontsize=8, loc="upper left")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-throughput.svg")

# 2. Where one vote's proving time goes at K=256 (seconds per vote)
parts = [("ballot-proof verification", 0.333, BLUE, BLUE_S),
         ("state work", 0.036, GREEN, GREEN_S),
         ("fixed pipeline / 256", 0.036, YELLOW, YELLOW_S),
         ("wrap / 256", 0.020, ORANGE, ORANGE_S)]
fig, ax = plt.subplots(figsize=(7.0, 2.2))
left = 0.0
for name, v, c, s in parts:
    ax.barh([0], [v], left=left, color=c, edgecolor=s, height=0.5)
    left += v
ax.text(0.333 / 2, 0, "verifying the ballot proof  0.333 s (78%)", ha="center", va="center", fontsize=9)
ax.text(0.351, 0.42, "state work 0.036", ha="center", fontsize=8, color=GREEN_S)
ax.text(0.387, -0.52, "pipeline 0.036", ha="center", fontsize=8, color=YELLOW_S)
ax.text(0.425, 0.42, "wrap 0.020", ha="center", fontsize=8, color=ORANGE_S)
ax.set_xlim(0, 0.46)
ax.set_ylim(-0.75, 0.75)
ax.set_yticks([])
ax.set_xlabel("GPU seconds per admitted ballot at 256 ballots per batch (measured components)")
ax.set_title("Where one vote's batch proving goes")
ax.spines["left"].set_visible(False)
save(fig, "annex-vote-cost.svg")

# 3. Warden GPU time (minutes, log): tally contribution vs worst-case complaints
sizes = ["10k casts", "120k casts", "1M casts"]
tally_min = [19 / 60, 60 / 60, 8.0]
compl_min = [10.7, 128, 1067]
w = 0.35
fig, ax = plt.subplots(figsize=(7.0, 3.6))
b1 = ax.bar(x - w / 2, tally_min, w, color=GREEN, edgecolor=GREEN_S,
            label="tally contribution proof, wrapped (routine)")
b2 = ax.bar(x + w / 2, compl_min, w, color=RED, edgecolor=RED_S,
            label="complaint proofs if every package were malformed")
ax.set_yscale("log")
for b, v, t in ((b1, tally_min, ["19 s", "≈1 min", "≈8 min"]), (b2, compl_min, ["11 min", "2.1 h", "17.8 h"])):
    for bb, vv, tt in zip(b, v, t):
        ax.text(bb.get_x() + bb.get_width() / 2, vv * 1.25, tt, ha="center", fontsize=9)
ax.set_xticks(x, sizes)
ax.set_ylabel("GPU time (minutes, log scale)")
ax.set_ylim(0.1, 4000)
ax.set_title("Warden GPU time, one RTX 5090 (extrapolated from measured runs)")
ax.legend(fontsize=8, loc="upper left")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-warden.svg")

# 4. Execution gas per voter, native settlement mode (econ.py)
cfg = ["ν=1\nθ=1", "ν=3\nθ=2", "ν=5\nθ=3", "ν=8\nθ=5"]
small = [4152, 13113, 20207, 30127]
big = [2638, 4387, 7249, 11648]
x4 = np.arange(4)
fig, ax = plt.subplots(figsize=(7.0, 3.6))
b1 = ax.bar(x4 - w / 2, small, w, color=YELLOW, edgecolor=YELLOW_S, label="500 voters")
b2 = ax.bar(x4 + w / 2, big, w, color=ORANGE, edgecolor=ORANGE_S, label="100,000 voters (120k casts)")
label(ax, b1, [f"{v/1000:.1f}k" for v in small], 400)
label(ax, b2, [f"{v/1000:.1f}k" for v in big], 400)
ax.set_xticks(x4, cfg)
ax.set_ylabel("execution gas per voter")
ax.set_ylim(0, 34000)
ax.set_title("Ethereum execution gas per voter, native settlement (measured parts + estimates)")
ax.legend(fontsize=8, loc="upper left")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-eth-cost.svg")

# 5. Voter: ballot proving time and memory per profile (piece-04, prototype circuit)
profiles = ["blowup 8\n34 queries", "fallback\n16 / 26q", "pinned\n32 / 18q"]
wasm_cold, native_1t, mem_mib = [2.45, 3.37, 5.16], [0.701, 1.049, 1.714], [122, 240, 478]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.4))
b1 = a1.bar(x - w / 2, native_1t, w, color=BLUE, edgecolor=BLUE_S, label="native, 1 thread")
b2 = a1.bar(x + w / 2, wasm_cold, w, color=GREEN, edgecolor=GREEN_S, label="WASM, cold (first proof)")
a1.axhline(10, ls="--", lw=1.2, color=RED_S)
a1.text(2.4, 10.25, "gate: 10 s", ha="right", fontsize=9, color=RED_S)
label(a1, b1, [f"{v:.1f}" for v in native_1t], 0.15)
label(a1, b2, [f"{v:.1f}" for v in wasm_cold], 0.15)
a1.set_xticks(x, profiles, fontsize=8)
a1.set_ylabel("seconds per ballot proof")
a1.set_ylim(0, 11.5)
a1.set_title("Proving time (desktop)", fontsize=10)
a1.legend(fontsize=8, loc="upper left")
a1.grid(axis="y", alpha=0.3)
b3 = a2.bar(x, mem_mib, 0.5, color=YELLOW, edgecolor=YELLOW_S)
a2.axhline(1536, ls="--", lw=1.2, color=RED_S)
a2.text(2.4, 1560, "gate: 1.5 GiB", ha="right", fontsize=9, color=RED_S)
label(a2, b3, [str(v) for v in mem_mib], 30)
a2.set_xticks(x, profiles, fontsize=8)
a2.set_ylabel("peak WASM linear memory (MiB)")
a2.set_ylim(0, 1750)
a2.set_title("Memory (CPU-independent)", fontsize=10)
a2.grid(axis="y", alpha=0.3)
fig.suptitle("Voter ballot proving, prototype circuit at the v3.0 profiles (measured)", fontsize=11)
save(fig, "annex-voter.svg")
