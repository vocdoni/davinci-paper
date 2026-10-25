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

# 1. Sequencer throughput vs batch size (RTX 5090, combined guest MEASURED, piece-07,
#    KEM payload included)
ks = ["32", "64", "128", "256"]
vps = [1.41, 1.92, 2.25, 2.46]
fig, ax = plt.subplots(figsize=(7.0, 3.4))
bars = ax.bar(ks, vps, color=GREEN, edgecolor=GREEN_S, width=0.6)
ax.axhline(2.71, ls="--", lw=1.2, color=BLUE_S)
ax.text(3.45, 2.74, "asymptote ≈2.7", ha="right", va="bottom", fontsize=9, color=BLUE_S)
for b, v in zip(bars, vps):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
ax.set_xlabel("batch size (ballots per batch proof)")
ax.set_ylabel("votes / second / GPU")
ax.set_ylim(0, 3.4)
ax.set_title("Sequencer throughput, one RTX 5090 (combined guest, measured end to end)")
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

# 5. Voter: ballot proving time and memory per profile (piece-04, prototype AIR)
profiles = ["blowup 8\n34 queries", "fallback\n16 / 26q", "pinned\n32 / 18q"]
wasm_cold = [2.45, 3.37, 5.16]
native_1t = [0.701, 1.049, 1.714]
mem_mib = [122, 240, 478]
x = np.arange(3)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.4))
b1 = a1.bar(x - w / 2, native_1t, w, color=BLUE, edgecolor=BLUE_S, label="native, 1 thread")
b2 = a1.bar(x + w / 2, wasm_cold, w, color=GREEN, edgecolor=GREEN_S, label="WASM, cold (first proof)")
a1.axhline(10, ls="--", lw=1.2, color=RED_S)
a1.text(2.4, 10.25, "gate: 10 s", ha="right", fontsize=9, color=RED_S)
for b, vals in [(b1, native_1t), (b2, wasm_cold)]:
    for bb, vv in zip(b, vals):
        a1.text(bb.get_x() + bb.get_width() / 2, vv + 0.15, f"{vv:.1f}", ha="center", fontsize=8)
a1.set_xticks(x, profiles, fontsize=8)
a1.set_ylabel("seconds per ballot proof")
a1.set_ylim(0, 11.5)
a1.set_title("Proving time (desktop)", fontsize=10)
a1.legend(fontsize=8, loc="upper left")
a1.grid(axis="y", alpha=0.3)
b3 = a2.bar(x, mem_mib, 0.5, color=YELLOW, edgecolor=YELLOW_S)
a2.axhline(1536, ls="--", lw=1.2, color=RED_S)
a2.text(2.4, 1560, "gate: 1.5 GB", ha="right", fontsize=9, color=RED_S)
for bb, vv in zip(b3, mem_mib):
    a2.text(bb.get_x() + bb.get_width() / 2, vv + 30, f"{vv}", ha="center", fontsize=8)
a2.set_xticks(x, profiles, fontsize=8)
a2.set_ylabel("peak WASM linear memory (MiB)")
a2.set_ylim(0, 1750)
a2.set_title("Memory (CPU-independent)", fontsize=10)
a2.grid(axis="y", alpha=0.3)
fig.suptitle("Voter ballot proving, prototype circuit at the v3.0 profiles (measured)", fontsize=11)
save(fig, "annex-voter.svg")
