# DAVINCI

This repository contains the academic paper describing the DAVINCI protocol for decentralized, verifiable, and privacy-preserving digital voting.

## Overview

As part of the ongoing [Vocdoni](https://vocdoni.io/) project, DAVINCI builds upon years of research and development in decentralized governance, introducing a new protocol architecture that combines:

- **Zero-knowledge proofs (ZK-SNARKs)** for verifiable computation,
- **Threshold homomorphic encryption** for private tallying,
- **Ethereum smart contracts** for transparent coordination.

The protocol provides end-to-end verifiability, receipt-freeness, and decentralized trust, enabling secure and scalable digital elections.

## Repository structure

```
├── LICENSE
├── README.md
├── v1/                 # Early draft version
└── v2/                 # Main paper source (current version)
    ├── build/          # Compiled files and LaTeX class/style files
    ├── figures/        # Diagrams and illustrations (.png, .drawio, .mmd, .pdf)
    ├── sections/       # Individual .tex files for each section
    ├── bibliography/   # References (bibtex.bib)
    └── misc/           # Miscellaneous materials (links, notes)
```

---

## Building the paper

To compile the paper locally:

```bash
cd v2/build
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The compiled file will be available at `v2/build/main.pdf`.

## Citation

If you use or reference this work, please cite:

> Escrich, P., Bellés-Muñoz, M., Piñana, J., Menéndez, L., Baig, R., & Muñoz-Tapia, J. L. (2025).  *DAVINCI: Decentralized autonomous vote integrity network with cryptographic inference.*  