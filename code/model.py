"""Core of the last-round chess model (see chess_thresholds_model.tex).

Two players choose S (settle) or F (fight).  Expected payoff of player i:

    EU_i(a) = u_ih + D(a) * g_i - c * 1{a_i = F}
    g_i     = q_i * U_i^+ - (1 - q_i) * U_i^-

with the threshold payoff u(x) = V * 1{x >= s + r} + eps * (x - s).
Everything here is a direct transcription of the propositions in the paper.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

S, F = 0, 1
ACTION_NAME = {S: "S", F: "F"}
TOL = 1e-12


@dataclass(frozen=True)
class Params:
    """Model parameters. D_* are P(decisive game) for each action profile.

    The defaults are ILLUSTRATIVE, not calibrated to any data set.
    """

    V: float = 1.0        # prize value
    eps: float = 0.05     # linear value of each point (rating / tie-break)
    cost: float = 0.01    # effort cost of fighting (same for both players)
    D_SS: float = 0.25
    D_SF: float = 0.45    # player 1 settles, player 2 fights
    D_FS: float = 0.45    # player 1 fights, player 2 settles
    D_FF: float = 0.75

    def __post_init__(self):
        # Assumption 1: strictly increasing in each argument
        assert 0 < self.D_SS < self.D_SF < self.D_FF < 1
        assert self.D_SS < self.D_FS < self.D_FF
        # Assumption 4: increasing differences (complementarity)
        assert self.D_FF - self.D_SF >= self.D_FS - self.D_SS - TOL
        assert self.D_FF - self.D_FS >= self.D_SF - self.D_SS - TOL

    def D(self, a1: int, a2: int) -> float:
        return {(S, S): self.D_SS, (S, F): self.D_SF,
                (F, S): self.D_FS, (F, F): self.D_FF}[(a1, a2)]


# ---------------------------------------------------------------------------
# Requirement cases (Proposition 4 in the paper)
# ---------------------------------------------------------------------------
CASES = ("i", "ii", "iii")
CASE_LABEL = {
    "i": "draw suffices",
    "ii": "win needed",
    "iii": "secured / out of reach",
}


def case_of(r: float) -> str:
    """Map the number of extra points r = T - s needed for the prize."""
    if r <= 0:
        return "iii"          # already secured
    if abs(r - 0.5) < 1e-9:
        return "i"            # a draw is enough
    if abs(r - 1.0) < 1e-9:
        return "ii"           # only a win is enough
    return "iii"              # out of reach


def steps(case: str, p: Params) -> tuple[float, float]:
    """(U+, U-) for a requirement case."""
    V, e = p.V, p.eps
    if case == "i":
        return e / 2, V + e / 2
    if case == "ii":
        return V + e / 2, e / 2
    return e / 2, e / 2


def rho(case: str, p: Params) -> float:
    up, um = steps(case, p)
    return um / (up + um)


# ---------------------------------------------------------------------------
# Equilibrium
# ---------------------------------------------------------------------------
def g_value(case: str, q_i: float, p: Params) -> float:
    up, um = steps(case, p)
    return q_i * up - (1 - q_i) * um


def gain_from_fighting(i: int, a_other: int, case_i: str, q_i: float,
                       p: Params) -> float:
    """EU_i(F, a_other) - EU_i(S, a_other)."""
    if i == 0:
        d_f, d_s = p.D(F, a_other), p.D(S, a_other)
    else:
        d_f, d_s = p.D(a_other, F), p.D(a_other, S)
    return g_value(case_i, q_i, p) * (d_f - d_s) - p.cost


def pure_equilibria(case1: str, case2: str, q: float,
                    p: Params) -> list[tuple[int, int]]:
    """All pure-strategy Nash equilibria; q = P(player 1 wins | decisive)."""
    out = []
    for a1, a2 in itertools.product((S, F), repeat=2):
        g1 = gain_from_fighting(0, a2, case1, q, p)
        g2 = gain_from_fighting(1, a1, case2, 1 - q, p)
        ok1 = g1 >= -TOL if a1 == F else g1 <= TOL
        ok2 = g2 >= -TOL if a2 == F else g2 <= TOL
        if ok1 and ok2:
            out.append((a1, a2))
    return out


def select_equilibrium(case1: str, case2: str, q: float, p: Params,
                       affiliated: bool) -> tuple[tuple[int, int], int]:
    """Pick one equilibrium; return (profile, number of pure equilibria).

    When both (S,S) and (F,F) are equilibria (both players 'conditional'),
    the focal point decides: affiliated pairs settle, others fight.
    """
    eq = pure_equilibria(case1, case2, q, p)
    if not eq:                       # cannot happen under Assumptions 1 and 4
        raise RuntimeError("no pure equilibrium found")
    if len(eq) == 1:
        return eq[0], 1
    if affiliated and (S, S) in eq:
        return (S, S), len(eq)
    if (F, F) in eq:
        return (F, F), len(eq)
    return eq[0], len(eq)


def regime_label(eq: list[tuple[int, int]]) -> str:
    key = tuple(sorted(ACTION_NAME[a1] + ACTION_NAME[a2] for a1, a2 in eq))
    names = {
        ("SS",): "Mutual settlement",
        ("FF",): "Mutual fight",
        ("FS",): "Player 1 fights, player 2 settles",
        ("SF",): "Player 1 settles, player 2 fights",
        ("FF", "SS"): "Coordination: both SS and FF",
    }
    return names.get(key, "other")
