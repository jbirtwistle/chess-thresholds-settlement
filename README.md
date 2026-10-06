# Thresholds, Risk and Settlement: Last-Round Draws in Chess

Data companion to a game-theoretic model of last-round draws in chess tournaments with payoff thresholds (prizes, title norms, qualification places).

- `docs/index.html` — the interactive page (model explorer, real last-round pairings, labelled synthetic simulation). Served by GitHub Pages from `/docs`.
- `paper/` — LaTeX source and PDF of the model section.
- `code/` — model, simulation, parsers, analysis and page-build scripts; `verify_model.py` checks the propositions numerically.
- `data/` — parsed pairings and analysis outputs. `final_round_pairings.csv` is **synthetic** (simulation); the `gs2025_*`, `menorca2026_*`, `aeroflot2026_*` files come from published tournament results.

Author: Ambrose Birtwistle.

Status: working draft, exploratory results. Tournament data come from public results pages (FIDE Grand Swiss 2025 game files; info64.org for Menorca 2026; chess-results.com for Aeroflot Open 2026): check their terms of use before redistributing.

Scripts use absolute paths from the original workspace (`/home/claude/chess_sim/...`); adjust before re-running.

## Publish with GitHub Pages
Settings → Pages → Deploy from a branch → `main` → `/docs`.

## License
Code and page: MIT License (see `LICENSE`). The tournament results in `data/` are public records published by the organisers of each event and are not covered by this license.
