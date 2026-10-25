#!/usr/bin/env python3
"""Generate Annex A charts for the v3-PQ spec from the PoC measurements (2026-10-25).

Numbers come from PoC_by_pieces/{piece-01..05}/RESULTS.md and poc/zisk-p3-verify.
Run: ~/.cache/chartenv/bin/python annex_charts.py   (writes ../annex-*.svg)
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt

GREEN, GREEN_S = "#d5e8d4", "#82b366"
BLUE, BLUE_S = "#dae8fc", "#6c8ebf"
YELLOW, YELLOW_S = "#fff2cc", "#d6b656"
ORANGE, ORANGE_S = "#ffe6cc", "#d79b00"
RED, RED_S = "#f8cecc", "#b85450"

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.edgecolor": "#999999",
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none",
})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"../{name}", format="svg")
    plt.close(fig)
    print(name)

# 1. Sequencer throughput vs batch size (RTX 5090, measured 0.338 s/vote + ~11.1 s/batch)
ks = ["32", "64", "128", "256"]
vps = [1.46, 1.96, 2.35, 2.62]
fig, ax = plt.subplots(figsize=(7.0, 3.4))
bars = ax.bar(ks, vps, color=GREEN, edgecolor=GREEN_S, width=0.6)
ax.axhline(2.96, ls="--", lw=1.2, color=BLUE_S)
ax.text(3.45, 2.99, "asymptote 2.96", ha="right", va="bottom", fontsize=9, color=BLUE_S)
for b, v in zip(bars, vps):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
ax.set_xlabel("batch size (ballots per batch proof)")
ax.set_ylabel("votes / second / GPU")
ax.set_ylim(0, 3.4)
ax.set_title("Sequencer throughput, one RTX 5090 (measured)")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-throughput.svg")

# 2. Where one vote's proving goes (K=256, measured steps)
fig, ax = plt.subplots(figsize=(7.0, 2.1))
parts = [("ballot-proof verification  2.62M", 2.62, BLUE, BLUE_S),
         ("state kernel  0.161M", 0.161, GREEN, GREEN_S),
         ("KEM payload share  0.014M", 0.014, ORANGE, ORANGE_S)]
left = 0.0
for label, v, c, s in parts:
    ax.barh([0], [v], left=left, color=c, edgecolor=s, height=0.5)
    left += v
ax.text(2.62 / 2, 0, "verification 94%", ha="center", va="center", fontsize=10)
ax.text(2.62 + 0.161 / 2, 0.45, "state kernel 5.8%", ha="center", fontsize=9, color=GREEN_S)
ax.text(2.62 + 0.161 + 0.25, -0.45, "ML-KEM payload 0.5% (per-batch, amortized at K=256)",
        ha="center", fontsize=9, color=ORANGE_S)
ax.set_xlim(0, 3.1)
ax.set_yticks([])
ax.set_xlabel("ZisK guest steps per admitted ballot (millions), measured")
ax.set_title("Where one vote's batch proving goes (ν=8, nf=16, measured)")
ax.spines["left"].set_visible(False)
save(fig, "annex-vote-cost.svg")

# 3. Warden GPU time: tally vs worst-case complaints (log minutes)
import numpy as np
sizes = ["10k casts", "120k casts", "1M casts"]
tally_min = [4 / 60, 52 / 60, 7.2]
compl_min = [10.7, 128, 1067]
x = np.arange(3)
w = 0.35
fig, ax = plt.subplots(figsize=(7.0, 3.6))
b1 = ax.bar(x - w / 2, tally_min, w, color=GREEN, edgecolor=GREEN_S,
            label="tally contribution proof (routine)")
b2 = ax.bar(x + w / 2, compl_min, w, color=RED, edgecolor=RED_S,
            label="complaint proofs, worst case: every package malformed")
ax.set_yscale("log")
for b, v, t in [(b1, tally_min, ["4 s", "52 s", "7.2 min"]),
                (b2, compl_min, ["11 min", "2.1 h", "17.8 h"])]:
    for bb, vv, tt in zip(b, v, t):
        ax.text(bb.get_x() + bb.get_width() / 2, vv * 1.25, tt, ha="center", fontsize=9)
ax.set_xticks(x, sizes)
ax.set_ylabel("GPU time (minutes, log scale)")
ax.set_ylim(0.03, 4000)
ax.set_title("Warden GPU time, one RTX 5090")
ax.legend(fontsize=9, loc="upper left")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-warden.svg")

# 4. Ethereum cost per election (log ETH)
fees = ["1 gwei", "10 gwei", "50 gwei"]
small = [0.0083, 0.083, 0.41]
big = [0.69, 6.9, 34.25]
x = np.arange(3)
fig, ax = plt.subplots(figsize=(7.0, 3.6))
b1 = ax.bar(x - w / 2, small, w, color=YELLOW, edgecolor=YELLOW_S, label="500 voters (5 batches)")
b2 = ax.bar(x + w / 2, big, w, color=ORANGE, edgecolor=ORANGE_S, label="100k voters (470 batches)")
ax.set_yscale("log")
for b, vals in [(b1, small), (b2, big)]:
    for bb, vv in zip(b, vals):
        ax.text(bb.get_x() + bb.get_width() / 2, vv * 1.25, f"{vv:g}", ha="center", fontsize=9)
ax.set_xticks(x, fees)
ax.set_ylabel("ETH per election (log scale)")
ax.set_ylim(0.004, 120)
ax.set_title("Ethereum cost per election (pessimistic blob pricing)")
ax.legend(fontsize=9, loc="upper left")
ax.grid(axis="y", alpha=0.3)
save(fig, "annex-eth-cost.svg")
