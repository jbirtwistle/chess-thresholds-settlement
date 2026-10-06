"""Collect everything the data page needs into one JSON blob.

Real data: the three last-round tables parsed earlier (Grand Swiss 2025 R11,
Menorca 2026 R9, Aeroflot 2026 R9).  Simulated data: the model-generated
pairings summarised by requirement pair.  Run with python3 -I.
"""
import json
from pathlib import Path

import pandas as pd

D = Path("/home/claude/chess_sim/data")
OUT = Path("/home/claude/chess_sim/page/data.json")
OUT.parent.mkdir(exist_ok=True)


def clean(name):
    return str(name).replace("*)", "").strip()


def rows_from(df, mapping, moves=False):
    out = []
    for _, r in df.iterrows():
        row = {
            "b": int(r[mapping["board"]]),
            "w": clean(r[mapping["white"]]), "sw": float(r[mapping["sw"]]), "ew": int(r[mapping["ew"]]),
            "k": clean(r[mapping["black"]]), "sb": float(r[mapping["sb"]]), "eb": int(r[mapping["eb"]]),
            "r": r[mapping["result"]], "d": int(r[mapping["draw"]]),
        }
        if moves:
            row["m"] = int(r["moves"])
        out.append(row)
    return out


def norm_result(x):
    return {"1/2-1/2": "½-½", "½-½": "½-½", "1-0": "1-0", "0-1": "0-1"}[str(x).strip()]


T = []

# ---- Grand Swiss 2025, round 11 ------------------------------------------
g = pd.read_csv(D / "gs2025_games_with_state.csv")
g = g[g["round"] == 11].copy()
g["result"] = g.result.map(norm_result)
leader = float(max(g.s_w.max(), g.s_b.max()))
T.append({
    "id": "gs", "name": "FIDE Grand Swiss 2025 (Open)", "short": "Grand Swiss R11",
    "round": 11, "rounds": 11, "leader": leader,
    "excluded": "none (all 58 games played)",
    "rows": rows_from(g, dict(board="board", white="white", sw="s_w", ew="white_elo", black="black",
                              sb="s_b", eb="black_elo", result="result", draw="draw"), moves=True),
})

# ---- Menorca 2026 round 9 and Aeroflot 2026 round 9 -------------------------
for tid, name, short, fn, rounds in [
    ("me", "V Open Chess Menorca 2026", "Menorca R9", "menorca2026_r9.csv", 9),
    ("ae", "Aeroflot Open 2026", "Aeroflot R9", "aeroflot2026_r9.csv", None),
]:
    a = pd.read_csv(D / fn)
    lead = float(max(a.white_score_before.max(), pd.to_numeric(a.black_score_before, errors="coerce").max()))
    p = a[a.kind == "played"].copy()
    p["result"] = p.result.map(norm_result)
    kinds = a.kind.value_counts().to_dict()
    exc = ", ".join(f"{kinds.get(k, 0)} {lab}" for k, lab in
                    [("forfeit", "forfeits"), ("bye", "bye"), ("absent", "unpaired with 0 points")] if kinds.get(k, 0))
    T.append({
        "id": tid, "name": name, "short": short, "round": 9, "rounds": rounds, "leader": lead,
        "excluded": exc,
        "rows": rows_from(p, dict(board="board", white="white", sw="white_score_before", ew="white_elo",
                                  black="black", sb="black_score_before", eb="black_elo",
                                  result="result", draw="draw")),
    })

# ---- simulation summary ----------------------------------------------------
s = pd.read_csv(D / "final_round_pairings.csv")
order = ["i", "ii", "iii"]
s["pair"] = [" / ".join(sorted([a, b], key=order.index)) for a, b in zip(s.case1, s.case2)]
s["profile"] = s.action1 + s.action2
sim_rows = []
for pair in ["i / i", "i / ii", "i / iii", "ii / ii", "ii / iii", "iii / iii"]:
    sub = s[s.pair == pair]
    prof = sub.profile.value_counts(normalize=True)
    main = ", ".join(f"{k} {v:.0%}" for k, v in prof.items() if v >= 0.05)
    sim_rows.append({"pair": pair, "n": int(len(sub)), "share": round(len(sub) / len(s), 4),
                     "draw": round(float(sub.draw.mean()), 4), "pdraw": round(float(sub.p_draw.mean()), 4),
                     "profiles": main})
SIM = {"n": int(len(s)), "tournaments": 2000, "rows": sim_rows, "overall_draw": round(float(s.draw.mean()), 4)}

json.dump({"tournaments": T, "sim": SIM}, open(OUT, "w"), ensure_ascii=False)
print("wrote", OUT, "| games:", {t["id"]: len(t["rows"]) for t in T})
for r in sim_rows:
    print(r)
