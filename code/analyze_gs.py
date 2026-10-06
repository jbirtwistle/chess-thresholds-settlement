"""Descriptive analysis of the FIDE Grand Swiss 2025 (Open), user-supplied PGNs.

EXPLORATORY.  The leader definition below ("both players within 0.5 points of
the leader going into the round") was fixed AFTER the author had seen the
round-11 top-board results, so p-values are descriptive, not confirmatory.
To limit the bias, round 11 is compared with the SAME definition applied to
earlier rounds.

Run:  python3 -I analyze_gs.py
"""
import json
import math
from pathlib import Path

import pandas as pd

D = Path("/home/claude/chess_sim/data")
L = pd.read_csv(D / "gs2025_player_games.csv")
G = pd.read_csv(D / "gs2025_games.csv")

# score before each round, and gap to the leader before that round
leader = L.groupby("round").score_before.max()
L["gap"] = L["round"].map(leader) - L.score_before
gap = L.set_index(["round", "pid"]).gap
G["gap_w"] = [gap[(r, p)] for r, p in zip(G["round"], G.white_id)]
G["gap_b"] = [gap[(r, p)] for r, p in zip(G["round"], G.black_id)]
sb = L.set_index(["round", "pid"]).score_before
G["s_w"] = [sb[(r, p)] for r, p in zip(G["round"], G.white_id)]
G["s_b"] = [sb[(r, p)] for r, p in zip(G["round"], G.black_id)]
G["top_pair"] = ((G.gap_w <= 0.5) & (G.gap_b <= 0.5)).astype(int)
G["mean_elo"] = (G.white_elo + G.black_elo) / 2
G["short_draw"] = ((G.draw == 1) & (G.moves <= 35)).astype(int)
G.to_csv(D / "gs2025_games_with_state.csv", index=False)


def fisher_two_sided(a, b, c, d):
    """Exact two-sided Fisher p for [[a,b],[c,d]] (no scipy dependency)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def pmf(x):
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    p_obs = pmf(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs + 1e-12)


rows = []
for r in range(2, 12):
    g = G[G["round"] == r]
    t = g[g.top_pair == 1]
    o = g[g.top_pair == 0]
    rows.append({
        "round": r, "n_top": len(t), "draws_top": int(t.draw.sum()),
        "draw_rate_top": round(t.draw.mean(), 3) if len(t) else None,
        "n_other": len(o), "draws_other": int(o.draw.sum()),
        "draw_rate_other": round(o.draw.mean(), 3),
        "mean_elo_top": round(t.mean_elo.mean()) if len(t) else None,
    })
T = pd.DataFrame(rows)
T.to_csv(D / "gs2025_draw_rates_by_round.csv", index=False)
print(T.to_string(index=False))

early = G[(G["round"].between(5, 10)) & (G.top_pair == 1)]
last = G[(G["round"] == 11) & (G.top_pair == 1)]
print(f"\nTop pairings, rounds 5-10: n={len(early)}, draws={int(early.draw.sum())}, "
      f"rate={early.draw.mean():.3f}, mean Elo {early.mean_elo.mean():.0f}")
print(f"Top pairings, round 11   : n={len(last)}, draws={int(last.draw.sum())}, "
      f"rate={last.draw.mean():.3f}, mean Elo {last.mean_elo.mean():.0f}")
p1 = fisher_two_sided(int(last.draw.sum()), len(last) - int(last.draw.sum()),
                      int(early.draw.sum()), len(early) - int(early.draw.sum()))
print(f"Fisher exact two-sided p (R11 top vs R5-10 top) = {p1:.3f}")

r11 = G[G["round"] == 11]
oth = r11[r11.top_pair == 0]
print(f"\nRound 11, non-top boards: n={len(oth)}, draws={int(oth.draw.sum())}, rate={oth.draw.mean():.3f}")
allo = G[(G["round"].between(2, 10)) & (G.top_pair == 0)]
print(f"Rounds 2-10, non-top boards: n={len(allo)}, draw rate={allo.draw.mean():.3f}")
print(f"Round 11, top vs non-top: Fisher p = "
      f"{fisher_two_sided(int(last.draw.sum()), len(last)-int(last.draw.sum()), int(oth.draw.sum()), len(oth)-int(oth.draw.sum())):.3f}")

print("\nShort draws (<=35 moves) by group:")
for name, sub in [("R2-10 all", G[G['round'].between(2, 10)]), ("R11 all", r11),
                  ("R5-10 top", early), ("R11 top", last)]:
    d = sub[sub.draw == 1]
    print(f"  {name:10s}: games={len(sub):3d} draws={len(d):3d} "
          f"short draws={int(sub.short_draw.sum()):3d} ({sub.short_draw.mean():.3f} of games) "
          f"median moves (draws)={d.moves.median():.0f}")

# --- the 7 top boards of round 11, as a table for the page ---
tb = last.sort_values(["s_w", "s_b"], ascending=False)[
    ["board", "white", "s_w", "white_elo", "black", "s_b", "black_elo", "result", "moves"]]
tb.to_csv(D / "gs2025_round11_top_boards.csv", index=False)
print("\nRound 11 top boards:"); print(tb.to_string(index=False))

# final standing (for context)
fin = L[L["round"] == 11].sort_values("score_after", ascending=False)[["name", "score_after"]]
fin.head(12).to_csv(D / "gs2025_final_top12.csv", index=False)

json.dump({
    "early_top": {"n": len(early), "draws": int(early.draw.sum())},
    "last_top": {"n": len(last), "draws": int(last.draw.sum())},
    "fisher_p_last_vs_early_top": p1,
}, open(D / "gs2025_summary.json", "w"), indent=1)
