"""Menorca 2026 round 9 (last round) + pooled with Grand Swiss 2025 round 11.

EXPLORATORY.  The 'top pairing' rule (both players within 0.5 points of the
leader going into the round) was defined on the Grand Swiss data.  The author
glimpsed the first rows of the Menorca file while inspecting its format, so
the Menorca check is nearly, not perfectly, out-of-sample.

Run: python3 -I analyze_menorca.py
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("/home/claude/chess_sim/data")
M = pd.read_csv(D / "menorca2026_r9.csv")
P = M[M.kind == "played"].copy()
leader = max(M.white_score_before.max(), pd.to_numeric(M.black_score_before, errors="coerce").max())
P["gap_w"] = leader - P.white_score_before
P["gap_b"] = leader - P.black_score_before
P["top_pair"] = ((P.gap_w <= 0.5) & (P.gap_b <= 0.5)).astype(int)
P["mean_elo"] = (P.white_elo + P.black_elo) / 2
P["elo_gap"] = (P.white_elo - P.black_elo).abs()
P["draw"] = P.draw.astype(int)
P.to_csv(D / "menorca2026_r9_played.csv", index=False)


def fisher(a, b, c, d):
    n = a + b + c + d
    r1, c1 = a + b, a + c
    pm = lambda x: math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)
    po = pm(a)
    return sum(pm(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if pm(x) <= po + 1e-12)


def logit(X, y, iters=50):
    """Plain IRLS logistic regression; returns coef, se."""
    X = np.column_stack([np.ones(len(X)), X])
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = X @ beta
        p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None])
        beta_new = beta + np.linalg.solve(H, X.T @ (y - p))
        if np.max(abs(beta_new - beta)) < 1e-10:
            beta = beta_new
            break
        beta = beta_new
    p = 1 / (1 + np.exp(-(X @ beta)))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    return beta, np.sqrt(np.diag(cov))


print(f"Leader score entering round 9: {leader}")
print(f"Played games: {len(P)}  | draws: {int(P.draw.sum())} ({P.draw.mean():.3f})")
t, o = P[P.top_pair == 1], P[P.top_pair == 0]
print(f"\nTop pairings: n={len(t)} draws={int(t.draw.sum())} rate={t.draw.mean():.3f} meanElo={t.mean_elo.mean():.0f}")
print(f"Other boards: n={len(o)} draws={int(o.draw.sum())} rate={o.draw.mean():.3f} meanElo={o.mean_elo.mean():.0f}")
print("Fisher p (top vs other) =",
      round(fisher(int(t.draw.sum()), len(t) - int(t.draw.sum()), int(o.draw.sum()), len(o) - int(o.draw.sum())), 3))
print("\nTop boards of Menorca R9:")
print(t[["board", "white", "white_score_before", "white_elo", "black", "black_score_before",
         "black_elo", "result"]].to_string(index=False))

# draw rate by score band (both players' mean score before the round)
P["band"] = pd.cut((P.white_score_before + P.black_score_before) / 2,
                   [-0.1, 3.0, 4.0, 5.0, 6.0, 7.1], labels=["<=3", "3.5-4", "4.5-5", "5.5-6", "6.5-7"])
print("\nDraw rate by mean score entering the round:")
print(P.groupby("band", observed=True).draw.agg(["size", "sum", "mean"]).round(3).to_string())

# rating-adjusted: draw ~ top_pair + mean_elo + |elo gap|
X = np.column_stack([P.top_pair, (P.mean_elo - 2200) / 100, P.elo_gap / 100])
b, se = logit(X, P.draw.values.astype(float))
print("\nLogit draw ~ top_pair + (meanElo-2200)/100 + |gap|/100  (Menorca R9, n=%d)" % len(P))
for nm, bb, ss in zip(["const", "top_pair", "meanElo/100", "|gap|/100"], b, se):
    print(f"  {nm:12s} {bb:7.3f}  (se {ss:.3f}, z={bb/ss:5.2f})  odds ratio {math.exp(bb):.2f}")

# ---------------- pool with Grand Swiss round 11 ----------------
G = pd.read_csv(D / "gs2025_games_with_state.csv")
G11 = G[G["round"] == 11]
rows = []
for name, sub in [("Grand Swiss R11", G11), ("Menorca R9", P)]:
    tt, oo = sub[sub.top_pair == 1], sub[sub.top_pair == 0]
    rows.append((name, len(tt), int(tt.draw.sum()), len(oo), int(oo.draw.sum())))
pool = pd.DataFrame(rows, columns=["last_round", "n_top", "draws_top", "n_other", "draws_other"])
pool.loc[len(pool)] = ["POOLED"] + [int(pool[c].sum()) for c in pool.columns[1:]]
pool["rate_top"] = (pool.draws_top / pool.n_top).round(3)
pool["rate_other"] = (pool.draws_other / pool.n_other).round(3)
print("\nLast rounds pooled:"); print(pool.to_string(index=False))
pr = pool.iloc[-1]
print("Pooled Fisher p (top vs other) =",
      round(fisher(int(pr.draws_top), int(pr.n_top - pr.draws_top),
                   int(pr.draws_other), int(pr.n_other - pr.draws_other)), 3))
pool.to_csv(D / "last_rounds_pooled.csv", index=False)
