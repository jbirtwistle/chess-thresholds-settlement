// Pure functions: the model (same equations as model.py) and the statistics.
// No DOM here, so the file can be tested in node against the Python code.
const S = 0, F = 1;
const MODEL = { V: 1, D: { "00": 0.25, "01": 0.45, "10": 0.45, "11": 0.75 } };
const TOL = 1e-12;

function Dprob(a1, a2) { return MODEL.D["" + a1 + a2]; }

// (U+, U-) for a requirement case: 'i' draw suffices, 'ii' win needed, 'iii' secured or out of reach
function steps(c, eps) {
  const V = MODEL.V;
  if (c === "i") return [eps / 2, V + eps / 2];
  if (c === "ii") return [V + eps / 2, eps / 2];
  return [eps / 2, eps / 2];
}
function rho(c, eps) { const [up, um] = steps(c, eps); return um / (up + um); }
function gValue(c, qi, eps) { const [up, um] = steps(c, eps); return qi * up - (1 - qi) * um; }

function gainFromFighting(i, aOther, c, qi, eps, cost) {
  const dF = i === 0 ? Dprob(F, aOther) : Dprob(aOther, F);
  const dS = i === 0 ? Dprob(S, aOther) : Dprob(aOther, S);
  return gValue(c, qi, eps) * (dF - dS) - cost;
}

// all pure Nash equilibria; q = P(player 1 wins | decisive game)
function pureEquilibria(c1, c2, q, eps, cost) {
  const out = [];
  for (const a1 of [S, F]) for (const a2 of [S, F]) {
    const g1 = gainFromFighting(0, a2, c1, q, eps, cost);
    const g2 = gainFromFighting(1, a1, c2, 1 - q, eps, cost);
    const ok1 = a1 === F ? g1 >= -TOL : g1 <= TOL;
    const ok2 = a2 === F ? g2 >= -TOL : g2 <= TOL;
    if (ok1 && ok2) out.push([a1, a2]);
  }
  return out;
}

// regime key for a set of equilibria
function regimeKey(eq) {
  const k = eq.map(([a, b]) => (a === S ? "S" : "F") + (b === S ? "S" : "F")).sort().join("+");
  return k; // SS, FF, FS, SF, FF+SS
}

// ---------- statistics ----------
function logChoose(n, k) {
  let s = 0;
  for (let i = 1; i <= k; i++) s += Math.log((n - k + i) / i);
  return s;
}
function fisherTwoSided(a, b, c, d) {
  const n = a + b + c + d, r1 = a + b, c1 = a + c;
  if (r1 === 0 || c1 === 0 || r1 === n || c1 === n) return NaN;
  const pm = (x) => Math.exp(logChoose(c1, x) + logChoose(n - c1, r1 - x) - logChoose(n, r1));
  const po = pm(a);
  let p = 0;
  for (let x = Math.max(0, r1 + c1 - n); x <= Math.min(r1, c1); x++) {
    const px = pm(x);
    if (px <= po + 1e-12) p += px;
  }
  return Math.min(1, p);
}
// Mantel-Haenszel common odds ratio with Robins-Breslow-Greenland 95% CI.
// strata: [[a,b,c,d]] with a=top&draw b=top&no-draw c=other&draw d=other&no-draw
function mantelHaenszel(strata) {
  let R = 0, Sx = 0, PR = 0, PSQR = 0, QS = 0;
  for (const [a, b, c, d] of strata) {
    const n = a + b + c + d;
    if (n === 0) continue;
    const P = (a + d) / n, Q = (b + c) / n, r = a * d / n, s = b * c / n;
    R += r; Sx += s; PR += P * r; PSQR += P * s + Q * r; QS += Q * s;
  }
  if (R === 0 || Sx === 0) return { or: NaN, lo: NaN, hi: NaN };
  const or = R / Sx;
  const se = Math.sqrt(PR / (2 * R * R) + PSQR / (2 * R * Sx) + QS / (2 * Sx * Sx));
  return { or, lo: Math.exp(Math.log(or) - 1.96 * se), hi: Math.exp(Math.log(or) + 1.96 * se) };
}

// a "top pairing": both players within thr points of the tournament leader going into the round
function isTop(row, leader, thr) {
  return leader - row.sw <= thr + 1e-9 && leader - row.sb <= thr + 1e-9;
}
function tally(t, thr) {
  let nt = 0, dt = 0, no = 0, dOther = 0;
  for (const r of t.rows) {
    if (isTop(r, t.leader, thr)) { nt++; dt += r.d; } else { no++; dOther += r.d; }
  }
  return { nTop: nt, dTop: dt, nOther: no, dOther };
}

if (typeof module !== "undefined") {
  module.exports = { S, F, MODEL, steps, rho, pureEquilibria, regimeKey, fisherTwoSided, mantelHaenszel, tally, isTop };
}
