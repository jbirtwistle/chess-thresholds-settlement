"""Parse the FIDE Grand Swiss 2025 (Open) PGNs into a games table.

Input : a directory with round-N/games.pgn  (user-supplied files)
Output: CSV with one row per game.  Run with  python3 -I parse_gs.py DIR OUT.csv
"""
import csv
import re
import sys
from pathlib import Path

HEADER = re.compile(r'^\[(\w+)\s+"(.*)"\]\s*$')
MOVENUM = re.compile(r'(\d+)\.(?!\.)')   # "12." but not "12..."
RESULT_PTS = {"1-0": (1.0, 0.0), "0-1": (0.0, 1.0), "1/2-1/2": (0.5, 0.5)}


def parse_pgn(text: str):
    games, hdr, moves, in_moves = [], {}, [], False
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            if in_moves:                      # a new game starts
                games.append((hdr, " ".join(moves)))
                hdr, moves, in_moves = {}, [], False
            hdr[m.group(1)] = m.group(2)
        elif line.strip():
            in_moves = True
            moves.append(line.strip())
    if hdr:
        games.append((hdr, " ".join(moves)))
    return games


def n_moves(movetext: str) -> int:
    clean = re.sub(r"\{[^}]*\}", " ", movetext)       # drop comments
    nums = [int(x) for x in MOVENUM.findall(clean)]
    return max(nums) if nums else 0


def main(indir: str, out: str) -> None:
    rows = []
    for rd in range(1, 12):
        path = Path(indir) / f"round-{rd}" / "games.pgn"
        for hdr, mt in parse_pgn(path.read_text(encoding="utf-8", errors="replace")):
            res = hdr.get("Result", "")
            if res not in RESULT_PTS:
                raise SystemExit(f"unexpected result {res!r} in round {rd}")
            w, b = RESULT_PTS[res]
            rows.append({
                "round": rd,
                "board": hdr["Round"].split(".")[1] if "." in hdr["Round"] else "",
                "white": hdr["White"], "black": hdr["Black"],
                "white_id": hdr.get("WhiteFideId", ""), "black_id": hdr.get("BlackFideId", ""),
                "white_elo": int(hdr["WhiteElo"]), "black_elo": int(hdr["BlackElo"]),
                "result": res, "white_pts": w, "black_pts": b,
                "draw": int(res == "1/2-1/2"), "moves": n_moves(mt),
            })
    with open(out, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} games -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
