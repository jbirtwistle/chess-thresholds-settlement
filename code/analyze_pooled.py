"""Three last rounds pooled: Grand Swiss 2025 R11, Menorca 2026 R9, Aeroflot 2026 R9.

EXPLORATORY.  The 'top pairing' rule was fixed on Grand Swiss; Menorca and
Aeroflot were not used to choose it (the author saw a few top-board results
while inspecting file formats).  Sensitivity to the threshold is reported.

Run: python3 -I analyze_pooled.py
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("/home/claude/chess_sim/data")


def load():
    out = {}
    g = pd.read_csv(D / "gs2025_games_with_state.csv")
    g = g[g["round"] == 11]
    lead = g[["s_w", "s_b"]].max().max()
    out["Grand Swiss 2025 R11"] = pd.DataFrame({
        "sw": g.s_w, "sb": g.s_b, "ew": g.white_elo, "eb": g.black_elo, "draw": g.draw,
        "white": g.white, "black": g.black, "result": g.result, "leader": lead})
    for key, fn in [("Menorca 2026 R9", "menorca2026_r9.csv"), ("Aeroflot 2026 R9", "aeroflot2026_r9.csv")]:
        a = pd.read_csv(D / fn)
        lead = max(a.white_score_before.max(),
                   pd.to_numeric(a.black_score_before, errors="coerce").max())
        p = a[a.kind == "played"]
        out[key] = pd.DataFrame({
            "sw": p.white_score_before.astype(float), "sb": p.black_score_before.astype(float),
            "ew": p.white_elo.astype(float), "eb": p.black_elo.astype(float),
            "draw": p.draw.astype(int), "white": p.white, "black": p.black,
            "result": p.result, "leader": lead})
    return out


def fisher(a, b, c, d):
    n = a + b + c + d
    r1, c1 = a + b, a + c
    pm = lambda x: math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)
    po = pm(a)
    return sum(pm(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if pm(x) <= po + 1e-12)


def mh(strata):
    """Mantel-Haenszel common odds ratio and RBG 95% CI.  strata = [(a,b,c,d)]
    a=top&draw b=top&no-draw c=other&draw d=other&no-draw."""
    R = S = PR = PSQR = QS = 0.0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n == 0:
            continue
        P, Q, r, s = (a + d) / n, (b + c) / n, a * d / n, b * c / n
        R += r; S += s; PR += P * r; PSQR += P * s + Q * r; QS += Q * s
    if R == 0 or S == 0:
        return float("nan"), float("nan"), float("nan")
    OR = R / S
    se = math.sqrt(PR / (2 * R * R) + PSQR / (2 * R * S) + QS / (2 * S * S))
    return OR, math.exp(math.log(OR) - 1.96 * se), math.exp(math.log(OR) + 1.96 * se)


def logit(X, y, iters=100):
    X = np.column_stack([np.ones(len(X)), X])
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta)))
        H = X.T @ (X * (p * (1 - p))[:, None])
        nb = beta + np.linalg.solve(H, X.T @ (y - p))
        if np.max(abs(nb - beta)) < 1e-10:
            beta = nb
            break
        beta = nb
    p = 1 / (1 + np.exp(-(X @ beta)))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    return beta, np.sqrt(np.diag(cov))


T = load()
summary_rows = []
for thr in (0.5, 1.0):
    print(f"\n================ threshold: both players within {thr} of the leader ================")
    strata = []
    for name, df in T.items():
        top = ((df.leader - df.sw <= thr) & (df.leader - df.sb <= thr)).astype(int)
        df[f"top_{thr}"] = top
        t, o = df[top == 1], df[top == 0]
        a, b = int(t.draw.sum()), len(t) - int(t.draw.sum())
        c, d = int(o.draw.sum()), len(o) - int(o.draw.sum())
        strata.append((a, b, c, d))
        p = fisher(a, b, c, d) if min(a + b, c + d) > 0 else float("nan")
        print(f"{name:24s} leader={df.leader.iloc[0]:.1f} | top: {a}/{a+b} draws"
              f" ({a/(a+b) if a+b else float('nan'):.2f}) | other: {c}/{c+d} ({c/(c+d):.2f})"
              f" | meanElo top {((t.ew+t.eb)/2).mean():.0f} vs other {((o.ew+o.eb)/2).mean():.0f}"
              f" | Fisher p={p:.3f}")
        summary_rows.append({"tournament": name, "threshold": thr, "n_top": a + b,
                             "draws_top": a, "n_other": c + d, "draws_other": c,
                             "fisher_p": round(p, 3)})
    OR, lo, hi = mh(strata)
    A, B, C, Dd = (sum(s[i] for s in strata) for i in range(4))
    print(f"POOLED crude: top {A}/{A+B} ({A/(A+B):.2f}) vs other {C}/{C+Dd} ({C/(C+Dd):.2f})")
    print(f"Mantel-Haenszel OR (stratified by tournament) = {OR:.2f}  95% CI [{lo:.2f}, {hi:.2f}]")

    # logit with tournament fixed effects and rating controls
    rows = []
    for k, (name, df) in enumerate(T.items()):
        for _, r in df.iterrows():
            rows.append([r[f"top_{thr}"], (r.ew + r.eb) / 2 / 100 - 22, abs(r.ew - r.eb) / 100,
                         int(k == 1), int(k == 2), r.draw])
    Z = np.array(rows, float)
    beta, se = logit(Z[:, :5], Z[:, 5])
    names = ["const", "top_pair", "meanElo/100", "|gap|/100", "Menorca FE", "Aeroflot FE"]
    print(f"Logit with tournament FE (n={len(Z)}):")
    for nm, bb, ss in zip(names, beta, se):
        print(f"   {nm:12s} {bb:7.3f} (se {ss:.3f}, z={bb/ss:5.2f})  OR {math.exp(bb):.2f}")
    if thr == 0.5:
        top_tbl = pd.concat([df.assign(tournament=n)[df[f"top_{thr}"] == 1] for n, df in T.items()])
        top_tbl[["tournament", "white", "sw", "ew", "black", "sb", "eb", "result"]].to_csv(
            D / "top_boards_all_tournaments.csv", index=False)

pd.DataFrame(summary_rows).to_csv(D / "pooled_summary.csv", index=False)
print("\nTop boards (threshold 0.5):")
print(pd.read_csv(D / "top_boards_all_tournaments.csv").to_string(index=False))
