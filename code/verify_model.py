"""Numerical check of the propositions of the last-round chess model.

Game: two players, actions S (settle) / F (fight).
D(a1,a2) = probability the game is decisive, strictly increasing in each argument.
Given decisive, player 1 wins with prob q (player 2 with 1-q).
Prize u_i nondecreasing at (s, s+1/2, s+1) = (u0, uh, u1).
EU_i = u0*P(loss) + uh*P(draw) + u1*P(win) - c_i*1{a_i = F}
"""
import itertools
import random

random.seed(12345)
S, F = 0, 1


def make_D(supermodular=False):
    # four values with D(S,S) < D(S,F), D(F,S) < D(F,F)
    while True:
        vals = sorted(random.uniform(0.02, 0.98) for _ in range(4))
        dss, dff = vals[0], vals[3]
        mid = [vals[1], vals[2]]
        random.shuffle(mid)
        dsf, dfs = mid
        D = {(S, S): dss, (S, F): dsf, (F, S): dfs, (F, F): dff}
        if supermodular:
            # delta_1(F) >= delta_1(S):  D(F,F)-D(S,F) >= D(F,S)-D(S,S)
            # delta_2(F) >= delta_2(S):  D(F,F)-D(F,S) >= D(S,F)-D(S,S)
            if not (dff - dsf >= dfs - dss and dff - dfs >= dsf - dss):
                continue
        return D


def make_u():
    a = sorted(random.uniform(0, 1) for _ in range(3))
    # allow flat steps sometimes (threshold-like prizes)
    r = random.random()
    if r < 0.15:
        a[1] = a[2]
    elif r < 0.3:
        a[1] = a[0]
    return a


def eu(i, a, D, q, u, c):
    d = D[a]
    qi = q if i == 0 else 1 - q
    w, l = d * qi, d * (1 - qi)
    u0, uh, u1 = u
    return u0 * l + uh * (1 - d) + u1 * w - c[i] * (a[i] == F)


def pure_ne(D, q, us, c, tol=1e-12):
    ne = []
    for a in itertools.product([S, F], repeat=2):
        ok = True
        for i in (0, 1):
            dev = list(a)
            dev[i] = 1 - a[i]
            if eu(i, tuple(dev), D, q, us[i], c) > eu(i, a, D, q, us[i], c) + tol:
                ok = False
        if ok:
            ne.append(a)
    return set(ne)


def g_of(i, q, u):
    qi = q if i == 0 else 1 - q
    up = u[2] - u[1]
    dn = u[1] - u[0]
    return qi * up - (1 - qi) * dn, up, dn


# ---------- Test 1: Prop 1 / Prop 2 (no effort cost) -----------------
bad = 0
N = 200000
for _ in range(N):
    D = make_D()
    q = random.uniform(0.02, 0.98)
    us = [make_u(), make_u()]
    c = [0.0, 0.0]
    g = [g_of(0, q, us[0])[0], g_of(1, q, us[1])[0]]
    if min(abs(x) for x in g) < 1e-9:
        continue
    ne = pure_ne(D, q, us, c)
    pred = (F if g[0] > 0 else S, F if g[1] > 0 else S)
    if ne != {pred}:
        bad += 1
    # draw-probability ordering
    drawp = {a: 1 - D[a] for a in D}
    assert drawp[(S, S)] > max(drawp[(S, F)], drawp[(F, S)])
    assert min(drawp[(S, F)], drawp[(F, S)]) > drawp[(F, F)]
print("Test 1 (dominant strategies = sign of g):", "OK" if bad == 0 else f"FAIL {bad}")

# ---------- Test 2: critical win share q* = U-/(U+ + U-) ----------------
bad = 0
for _ in range(200000):
    u = make_u()
    up, dn = u[2] - u[1], u[1] - u[0]
    if up + dn < 1e-9:
        continue
    qstar = dn / (up + dn)
    q = random.uniform(0.001, 0.999)
    g = q * up - (1 - q) * dn
    if abs(q - qstar) < 1e-9:
        continue
    if (g > 0) != (q > qstar):
        bad += 1
print("Test 2 (q* cutoff):", "OK" if bad == 0 else f"FAIL {bad}")

# ---------- Test 3: threshold prizes + eps tie-break (Corollary) -----------
bad = 0
for _ in range(200000):
    q = random.uniform(0.02, 0.98)
    V = random.uniform(0.5, 2.0)
    qi = q
    # n = 1/2: draw suffices ; u(s)=0, u(s+1/2)=V, u(s+1)=V, plus eps*S
    # n = 1  : win needed    ; u(s)=0, u(s+1/2)=0, u(s+1)=V
    eps_max_draw = 2 * (1 - qi) * V / max(2 * qi - 1, 1e-12) if qi > 0.5 else 1e9
    eps_max_win = 2 * qi * V / max(1 - 2 * qi, 1e-12) if qi < 0.5 else 1e9
    eps = random.uniform(0, 0.99) * min(eps_max_draw, eps_max_win, 5.0)
    # draw-suffices
    u = [0 + 0 * eps, V + eps / 2, V + eps]
    g = g_of(0, qi, u)[0]
    if not g < 0:
        bad += 1
    # win-needed
    u = [0, 0 + eps / 2, V + eps]
    g = g_of(0, qi, u)[0]
    if not g > 0:
        bad += 1
    # dead (secured/unreachable): u = const + eps*S -> g = (eps/2)(2q-1)
    u = [0, eps / 2, eps]
    g = g_of(0, qi, u)[0]
    if abs(g - (eps / 2) * (2 * qi - 1)) > 1e-12:
        bad += 1
print("Test 3 (threshold prizes):", "OK" if bad == 0 else f"FAIL {bad}")

# ---------- Test 4: effort costs and complementarity (Prop 5) -------------
bad = 0
cnt = {"both_cond": 0, "mixed": 0}
for _ in range(300000):
    D = make_D(supermodular=True)
    q = random.uniform(0.02, 0.98)
    us = [make_u(), make_u()]
    c = [random.uniform(0.005, 0.4), random.uniform(0.005, 0.4)]
    g = [g_of(0, q, us[0])[0], g_of(1, q, us[1])[0]]
    d1 = {a2: D[(F, a2)] - D[(S, a2)] for a2 in (S, F)}
    d2 = {a1: D[(a1, F)] - D[(a1, S)] for a1 in (S, F)}
    dl = [d1, d2]
    types = []
    skip = False
    for i in (0, 1):
        lo = g[i] * dl[i][S] - c[i]   # gain from F when opponent plays S
        hi = g[i] * dl[i][F] - c[i]   # gain from F when opponent plays F
        if min(abs(lo), abs(hi)) < 1e-9:
            skip = True
        if lo > 0:
            types.append("F")      # F dominant
        elif hi < 0:
            types.append("S")      # S dominant
        else:
            types.append("C")      # conditional: F iff opponent F
    if skip:
        continue
    ne = pure_ne(D, q, us, c)
    # predicted set
    pred = set()
    for a in itertools.product([S, F], repeat=2):
        ok = True
        for i in (0, 1):
            t = types[i]
            if t == "F" and a[i] != F:
                ok = False
            if t == "S" and a[i] != S:
                ok = False
            if t == "C" and a[i] != a[1 - i]:
                ok = False
        if ok:
            pred.add(a)
    if types == ["C", "C"]:
        cnt["both_cond"] += 1
        if ne != {(S, S), (F, F)}:
            bad += 1
    elif "C" in types:
        cnt["mixed"] += 1
    if ne != pred:
        bad += 1
print("Test 4 (cost + complementarity classification):", "OK" if bad == 0 else f"FAIL {bad}", cnt)

# ---------- Test 5: scoring-rule share of draw-sufficient requirements -----
from fractions import Fraction
for (w, d) in [(1, Fraction(1, 2)), (3, 1)]:
    d = Fraction(d)
    w = Fraction(w)
    m = int(w / d)
    live = [d * k for k in range(1, m + 1)]
    draw_suff = [n for n in live if n <= d]
    print(f"Scoring (win={w}, draw={d}): live n = {[str(x) for x in live]}, share draw-suffices = {len(draw_suff)}/{len(live)}, both-defenders (indep.) = {Fraction(len(draw_suff), len(live))**2}")
