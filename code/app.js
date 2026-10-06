(function () {
  const T = window.__DATA__.tournaments, SIM = window.__DATA__.sim;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x) => Math.round(x * 100) + "%";
  const fnum = (x) => (Math.abs(x) >= 10 ? x.toFixed(1) : x.toFixed(2));
  let THR = 0.5;

  /* ---------------- model explorer ---------------- */
  const REG = {
    SS: { name: "Both settle", short: "Settle", col: "--s1" },
    FF: { name: "Both fight", short: "Fight", col: "--s2" },
    FS: { name: "Player 1 fights, player 2 settles", short: "P1 fights", col: "--s3" },
    SF: { name: "Player 1 settles, player 2 fights", short: "P2 fights", col: "--s3" },
    "FF+SS": { name: "Two equilibria: both settle or both fight", short: "SS or FF", col: "--neutral" },
  };
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function textOn(hex) {
    const m = /^#([0-9a-f]{6})$/i.exec(hex);
    if (!m) return cssVar("--ink");
    const v = [0, 2, 4].map((i) => parseInt(m[1].substr(i, 2), 16) / 255)
      .map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
    const L = 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
    return L > 0.3 ? "#0f1720" : "#ffffff";
  }
  const regOf = (k) => REG[k] || { name: "Other", short: "", col: "--neutral" };

  function renderExplorer() {
    const c1 = $("c1").value, c2 = $("c2").value;
    const q = +$("q").value, eps = +$("eps").value, cost = +$("cost").value;
    $("qv").textContent = q.toFixed(2); $("epsv").textContent = eps.toFixed(2); $("costv").textContent = cost.toFixed(3);

    // strip across q
    const N = 400, runs = [];
    for (let k = 0; k < N; k++) {
      const key = regimeKey(pureEquilibria(c1, c2, (k + 0.5) / N, eps, cost));
      if (runs.length && runs[runs.length - 1].key === key) runs[runs.length - 1].len++;
      else runs.push({ key, len: 1 });
    }
    const w = $("strip").clientWidth || 600;
    $("strip").innerHTML = runs.map((r) => {
      const R = regOf(r.key), hex = cssVar(R.col), fits = (r.len / N) * w >= R.short.length * 7.4 + 16;
      return `<div class="seg-r" style="flex:${r.len} 1 0;background:var(${R.col});color:${textOn(hex)}" title="${esc(R.name)}">${fits ? esc(R.short) : ""}</div>`;
    }).join("");
    const used = [...new Set(runs.map((r) => r.key))];
    const legendKeys = used.map((k) => ({ k, R: regOf(k) }));
    $("legend").innerHTML = legendKeys.map(({ R }) => `<span><i style="background:var(${R.col})"></i>${esc(R.name)}</span>`).join("");
    $("marker").style.left = (q * 100) + "%";
    $("markerlab").textContent = "q = " + q.toFixed(2);

    // readout at current q
    const eq = pureEquilibria(c1, c2, q, eps, cost), key = regimeKey(eq), R = regOf(key);
    $("ro-eq").textContent = R.name;
    $("ro-eq-s").textContent = eq.length > 1
      ? "Each is self-enforcing. A shared team, club or friendship can make one of them the focal point."
      : "A single equilibrium in pure strategies.";
    const drawP = eq.map(([a, b]) => 1 - MODEL.D["" + a + b]);
    $("ro-draw").textContent = eq.length > 1 ? drawP.map(pct).join(" or ") : pct(drawP[0]);
    $("ro-draw-s").textContent = eq.length > 1 ? "Both settle: " + pct(1 - MODEL.D["00"]) + ". Both fight: " + pct(1 - MODEL.D["11"]) + "." : "Chance the game ends without a winner.";
    const r1 = rho(c1, eps), r2 = rho(c2, eps), sum = r1 + r2;
    $("ro-rho").textContent = `ρ₁ ${r1.toFixed(2)} · ρ₂ ${r2.toFixed(2)}`;
    let msg;
    if (sum > 1 + 1e-9) msg = `Sum ${sum.toFixed(2)} is above 1: both settle when q is between ${(1 - r2).toFixed(2)} and ${r1.toFixed(2)}.`;
    else if (sum < 1 - 1e-9) msg = `Sum ${sum.toFixed(2)} is below 1: both fight when q is between ${r1.toFixed(2)} and ${(1 - r2).toFixed(2)}.`;
    else msg = "Sum is 1: there is no range of q where both settle or both fight.";
    $("ro-rho-s").textContent = msg + " The strip above includes the cost of fighting you set.";
  }

  /* ---------------- real data ---------------- */
  const tip = $("tip");
  function showTip(text, x, y) { tip.textContent = text; tip.hidden = false; const r = tip.getBoundingClientRect(); tip.style.left = Math.min(window.innerWidth - r.width - 8, Math.max(8, x + 12)) + "px"; tip.style.top = Math.max(8, y - r.height - 10) + "px"; }
  function hideTip() { tip.hidden = true; }

  function renderReal() {
    const groups = T.map((t) => ({ label: t.short, ...tally(t, THR), t }));
    const tot = groups.reduce((a, g) => ({ nTop: a.nTop + g.nTop, dTop: a.dTop + g.dTop, nOther: a.nOther + g.nOther, dOther: a.dOther + g.dOther }), { nTop: 0, dTop: 0, nOther: 0, dOther: 0 });
    const strata = groups.map((g) => [g.dTop, g.nTop - g.dTop, g.dOther, g.nOther - g.dOther]);
    const mh = mantelHaenszel(strata);
    const topRate = tot.dTop / tot.nTop, otherRate = tot.dOther / tot.nOther;

    $("tiles").innerHTML = `
      <div class="tile"><div class="k">Top pairings drawn</div><div class="big">${pct(topRate)}</div><div class="s">${tot.dTop} of ${tot.nTop} games</div></div>
      <div class="tile"><div class="k">All other boards drawn</div><div class="big">${pct(otherRate)}</div><div class="s">${tot.dOther} of ${tot.nOther} games</div></div>
      <div class="tile"><div class="k">Odds of a draw, top versus other</div><div class="big">${fnum(mh.or)}×</div><div class="s">95% interval ${fnum(mh.lo)} to ${fnum(mh.hi)}, by tournament</div></div>`;

    const all = [...groups, { label: "All three", ...tot }];
    const rate = (d, n) => (n ? d / n : null);
    $("plot").innerHTML = [0, 25, 50, 75, 100].map((p) => `<div class="grid-l${p === 0 ? " base" : ""}" style="top:${100 - p}%"><span>${p}%</span></div>`).join("") +
      `<div class="groups">` + all.map((g) => {
        const rt = rate(g.dTop, g.nTop), ro = rate(g.dOther, g.nOther);
        const col = (r, d, n, name, c) => r === null
          ? `<div class="bcol" tabindex="0" data-tip="${esc(g.label)}: no ${name} in this tournament at this threshold."><div class="bval" style="bottom:0;color:var(--muted);font-weight:400">n = 0</div></div>`
          : `<div class="bcol" tabindex="0" data-tip="${esc(g.label)}, ${name}: ${d} of ${n} games drawn (${pct(r)})."><div class="bar" style="height:${r * 100}%;background:var(${c})"></div><div class="bval" style="bottom:${r * 100}%">${pct(r)}</div></div>`;
        return `<div class="group">${col(rt, g.dTop, g.nTop, "top pairings", "--s1")}${col(ro, g.dOther, g.nOther, "other boards", "--s2")}</div>`;
      }).join("") + `</div>`;
    $("xlabels").innerHTML = all.map((g) => `<div>${esc(g.label)}<small>${g.nTop} top · ${g.nOther} other</small></div>`).join("");

    $("counts").innerHTML = `<thead><tr><th>Tournament</th><th class="n">Top games</th><th class="n">Top drawn</th><th class="n">Top rate</th><th class="n">Other games</th><th class="n">Other drawn</th><th class="n">Other rate</th><th class="n">Fisher p</th></tr></thead><tbody>` +
      groups.map((g) => {
        const p = fisherTwoSided(g.dTop, g.nTop - g.dTop, g.dOther, g.nOther - g.dOther);
        return `<tr><td>${esc(g.t.name)}</td><td class="n">${g.nTop}</td><td class="n">${g.dTop}</td><td class="n">${g.nTop ? pct(g.dTop / g.nTop) : "–"}</td><td class="n">${g.nOther}</td><td class="n">${g.dOther}</td><td class="n">${pct(g.dOther / g.nOther)}</td><td class="n">${isNaN(p) ? "–" : p.toFixed(2)}</td></tr>`;
      }).join("") + `</tbody>`;

    const incl = mh.lo <= 1 && mh.hi >= 1;
    const adj = THR === 0.5
      ? "Controlling for tournament and average rating, the odds ratio for top pairings is 2.2 (z = 1.1); each 100 points of average rating multiply the odds of a draw by 1.2 (z = 2.2). Aeroflot has no top pairing at this threshold."
      : "Controlling for tournament and average rating, the odds ratio for top pairings is 1.5 (z = 0.9); each 100 points of average rating multiply the odds of a draw by 1.2 (z = 2.0).";
    $("adj").innerHTML = `<b>${incl ? "The interval includes 1." : "The interval excludes 1."}</b> ${incl ? "The data do not rule out that top pairings draw no more often than other boards." : ""} ${adj}`;
    renderTable();
  }

  /* ---------------- pairings table ---------------- */
  let TID = T[0].id;
  function renderTabs() {
    $("tabs").innerHTML = T.map((t) => `<button role="tab" type="button" data-id="${t.id}" aria-selected="${t.id === TID}">${esc(t.short)}</button>`).join("");
    for (const b of $("tabs").querySelectorAll("button")) b.onclick = () => { TID = b.dataset.id; renderTabs(); renderTable(); };
  }
  const sc = (x) => x.toFixed(1);
  function renderTable() {
    const t = T.find((x) => x.id === TID);
    const q = $("search").value.trim().toLowerCase(), topOnly = $("toponly").checked, sort = $("sort").value;
    let rows = t.rows.map((r) => ({ ...r, top: isTop(r, t.leader, THR) }));
    if (q) rows = rows.filter((r) => (r.w + " " + r.k).toLowerCase().includes(q));
    if (topOnly) rows = rows.filter((r) => r.top);
    rows.sort((a, b) => sort === "score" ? (b.sw + b.sb) - (a.sw + a.sb) || a.b - b.b : sort === "elo" ? (b.ew + b.eb) - (a.ew + a.eb) || a.b - b.b : a.b - b.b);
    $("tmeta").textContent = `${t.name} · round ${t.round}${t.rounds ? " of " + t.rounds : ""} · leader going in: ${t.leader.toFixed(1)} · ${t.rows.length} games · not shown: ${t.excluded}.` +
      ` Showing ${rows.length}. Top pairing: within ${THR === 1 ? "1 point" : "0.5 points"} of the leader (set above).`;
    $("ptable").innerHTML = `<thead><tr><th class="n">Bo.</th><th>White</th><th class="n">Pts</th><th class="n">Elo</th><th style="text-align:center">Result</th><th>Black</th><th class="n">Pts</th><th class="n">Elo</th><th></th></tr></thead><tbody>` +
      rows.map((r) => `<tr><td class="n">${r.b}</td><td>${esc(r.w)}</td><td class="n">${sc(r.sw)}</td><td class="n">${r.ew}</td><td class="res${r.d ? " dr" : ""}">${esc(r.r)}</td><td>${esc(r.k)}</td><td class="n">${sc(r.sb)}</td><td class="n">${r.eb}</td><td>${r.top ? '<span class="toppill">TOP</span>' : ""}</td></tr>`).join("") + `</tbody>`;
    const cell = (s) => (/[",\n]/.test(s) ? '"' + String(s).replace(/"/g, '""') + '"' : s);
    $("csv").value = ["tournament,round,board,white,white_score_before,white_elo,black,black_score_before,black_elo,result,top_pairing"]
      .concat(t.rows.map((r) => [t.name, t.round, r.b, r.w, r.sw, r.ew, r.k, r.sb, r.eb, r.r, isTop(r, t.leader, THR) ? 1 : 0].map(cell).join(","))).join("\n");
    $("copied").textContent = "";
  }

  /* ---------------- simulation ---------------- */
  function renderSim() {
    const pctw = (x) => (x * 100).toFixed(1) + "%";
    $("hbars").innerHTML = SIM.rows.map((r) => `<div class="hrow"><div class="lbl">${esc(r.pair)}<small>${r.n.toLocaleString("en-US")} games</small></div>
      <div class="htrack"><div class="hgrid" style="left:25%"></div><div class="hgrid" style="left:50%"></div><div class="hgrid" style="left:75%"></div>
      <div class="hbar" style="width:${r.draw * 100}%"></div><div class="hval" style="left:${r.draw * 100}%">${pct(r.draw)}</div></div></div>`).join("");
    $("simtable").innerHTML = `<thead><tr><th>Needs (P1 / P2)</th><th class="n">Games</th><th class="n">Share</th><th>Equilibrium played</th><th class="n">Drawn</th><th class="n">Model draw probability</th></tr></thead><tbody>` +
      SIM.rows.map((r) => `<tr><td>${esc(r.pair)}</td><td class="n">${r.n.toLocaleString("en-US")}</td><td class="n">${pctw(r.share)}</td><td>${esc(r.profiles)}</td><td class="n">${pctw(r.draw)}</td><td class="n">${pctw(r.pdraw)}</td></tr>`).join("") + `</tbody>`;
  }

  /* ---------------- wiring ---------------- */
  for (const id of ["c1", "c2", "q", "eps", "cost"]) $(id).addEventListener("input", renderExplorer);
  for (const r of document.querySelectorAll('input[name="thr"]')) r.addEventListener("change", () => { THR = +r.value; renderReal(); });
  for (const id of ["search", "sort", "toponly"]) $(id).addEventListener("input", renderTable);
  $("copy").addEventListener("click", () => {
    const ta = $("csv"), done = (m) => { $("copied").textContent = m; };
    const fallback = () => { ta.focus(); ta.select(); done("Press Ctrl+C or ⌘C to copy the selected text."); };
    try { navigator.clipboard.writeText(ta.value).then(() => done("Copied."), fallback); } catch (e) { fallback(); }
  });
  const plot = $("plot");
  plot.addEventListener("mouseover", (e) => { const b = e.target.closest(".bcol"); if (b) showTip(b.dataset.tip, e.clientX, e.clientY); });
  plot.addEventListener("mousemove", (e) => { const b = e.target.closest(".bcol"); if (b) showTip(b.dataset.tip, e.clientX, e.clientY); else hideTip(); });
  plot.addEventListener("mouseleave", hideTip);
  plot.addEventListener("focusin", (e) => { const b = e.target.closest(".bcol"); if (b) { const r = b.getBoundingClientRect(); showTip(b.dataset.tip, r.left, r.top); } });
  plot.addEventListener("focusout", hideTip);
  window.addEventListener("resize", renderExplorer);
  try { new MutationObserver(renderExplorer).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] }); } catch (e) {}
  try { window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderExplorer); } catch (e) {}

  renderExplorer(); renderReal(); renderTabs(); renderTable(); renderSim();
})();
