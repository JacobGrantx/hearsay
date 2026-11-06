"use strict";
// Decodes the inlined run (window.RUN) and builds the indices the renderer and panel use.
// Everything the viewer shows is derived from these logs alone.
const V = (window.V = {});

V.gunzipText = async function (b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Response(stream).text();
};

const parseLines = (text) => text.split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
const fieldIndex = (fields) => Object.fromEntries(fields.map((f, i) => [f, i]));

V.loadRun = async function (raw) {
  const L = raw.layout;
  const rows = parseLines(await V.gunzipText(raw.state));
  const events = raw.events ? parseLines(await V.gunzipText(raw.events)) : [];
  const run = {
    name: raw.name || "",
    layout: L,
    metrics: raw.metrics || [],
    vocab: raw.vocab || null,  // the words the AI bees read; null for scripted bees
    bf: fieldIndex(L.bee_fields || ["id", "x", "y", "life", "carrying", "stunned", "intent"]),
    hf: fieldIndex(L.hornet_fields || ["id", "x", "y", "smell", "hearing", "ambush", "target", "mode"]),
    sf: fieldIndex(L.sound_fields || ["bee", "x", "y", "sound"]),
    lifeCap: L.life_cap || 3 * (L.base_life || 250),
    seasonNames: L.season_names || ["spring", "summer", "autumn", "winter"],
  };
  // Dense tick array: ticks[t] is the state written after tick t resolved.
  const last = rows.length ? rows[rows.length - 1].t : 0;
  run.ticks = new Array(last + 1);
  for (const r of rows) run.ticks[r.t] = r;
  for (let t = 0; t <= last; t++) if (!run.ticks[t]) run.ticks[t] = run.ticks[t - 1] || { t, s: 0, y: 0, b: [], h: [], snd: [] };
  run.lastTick = last;
  run._beeMaps = new Map();
  run._hornetMaps = new Map();

  // Sounds as a flat, time-sorted list.
  run.sounds = [];
  for (const r of rows) {
    for (const s of r.snd || []) {
      run.sounds.push({ t: r.t, bee: s[run.sf.bee], x: s[run.sf.x], y: s[run.sf.y], sound: s[run.sf.sound] });
    }
  }

  // Visual effects and per-bee histories from the events log.
  run.fx = [];
  run.bees = new Map();
  const bee = (id) => {
    if (!run.bees.has(id)) {
      run.bees.set(id, { id, born: null, cause: null, died: null, decisions: [], heard: [], said: [], stings: [], deliveries: [], heals: [] });
    }
    return run.bees.get(id);
  };
  run.seasonEvents = [];
  for (const e of events) {
    switch (e.kind) {
      case "hatch":
      case "queen_hatch": {
        const b = bee(e.bee);
        b.born = e.t;
        b.cause = e.kind === "queen_hatch" ? "queen" : e.cause;
        run.fx.push({ kind: "hatch", t: e.t, x: e.x, y: e.y, bee: e.bee, queen: e.kind === "queen_hatch" });
        break;
      }
      case "death":
        bee(e.bee).died = e.t;
        run.fx.push({ kind: "death", t: e.t, x: e.x, y: e.y, bee: e.bee });
        break;
      case "sting":
        bee(e.bee).stings.push(e);
        run.fx.push({ kind: "sting", t: e.t, x: e.x, y: e.y, bee: e.bee, hornet: e.hornet, amount: e.amount });
        break;
      case "delivery":
        bee(e.bee).deliveries.push(e);
        run.fx.push({ kind: "delivery", t: e.t, bee: e.bee });
        break;
      case "heal":
        bee(e.bee).heals.push(e);
        break;
      case "decision":
        bee(e.bee).decisions.push(e);
        break;
      case "say":
        bee(e.bee).said.push(e);
        for (const h of e.heard_by || []) bee(h).heard.push({ t: e.t, from: e.bee, text: e.text });
        break;
      case "season":
        run.seasonEvents.push(e);
        break;
    }
  }
  run.fx.sort((a, b) => a.t - b.t);
  run.events = events;
  return run;
};

// Index of the first element of a t-sorted array with t >= value.
V.lowerBound = function (arr, value) {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid].t < value) lo = mid + 1; else hi = mid;
  }
  return lo;
};

// Items of a t-sorted array with from <= t <= to.
V.between = function (arr, from, to) {
  const out = [];
  for (let i = V.lowerBound(arr, from); i < arr.length && arr[i].t <= to; i++) out.push(arr[i]);
  return out;
};

V.tickState = (run, t) => run.ticks[Math.max(0, Math.min(run.lastTick, t))];

V.beeMap = function (run, t) {
  t = Math.max(0, Math.min(run.lastTick, t));
  let m = run._beeMaps.get(t);
  if (!m) {
    m = new Map(run.ticks[t].b.map((b) => [b[run.bf.id], b]));
    if (run._beeMaps.size > 64) run._beeMaps.clear();
    run._beeMaps.set(t, m);
  }
  return m;
};

V.hornetMap = function (run, t) {
  t = Math.max(0, Math.min(run.lastTick, t));
  let m = run._hornetMaps.get(t);
  if (!m) {
    m = new Map(run.ticks[t].h.map((h) => [h[run.hf.id], h]));
    if (run._hornetMaps.size > 64) run._hornetMaps.clear();
    run._hornetMaps.set(t, m);
  }
  return m;
};

// Counts of colony events in [from, to], used by the panel's season summary.
V.countEvents = function (run, from, to) {
  const c = { delivery: 0, sting: 0, hatch: 0, death: 0 };
  for (const f of V.between(run.fx, from, to)) c[f.kind] = (c[f.kind] || 0) + 1;
  return c;
};
