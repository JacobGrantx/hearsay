"use strict";
// Page wiring: canvas sizing, the view transform, playback, controls, and capture mode.
// Hash parameters: #t=120&bee=3 opens at a tick with a bee selected.
// Capture mode: #capture&from=T0&to=T1&step=S[&bee=ID][&view=x0,y0,x1,y1]; a script then calls
// window.__capture.frame(i) for i in [0, count) and screenshots each frame.

V.state = { tau: 0, playing: false, speed: 6, sel: null, view: { scale: 1, ox: 0, oy: 0 }, userView: false, drawn: [] };

const $ = (id) => document.getElementById(id);
let canvas, ctx, cssW = 0, cssH = 0, dpr = 1, region = null, renderQueued = false;

V.fitView = function () {
  const L = V.run.layout, st = V.state;
  const [x0, y0, x1, y1] = region || [0, 0, L.width, L.height];
  const pad = 14, scale = Math.min((cssW - 2 * pad) / (x1 - x0), (cssH - 2 * pad) / (y1 - y0));
  st.view = { scale, ox: (cssW - scale * (x1 + x0)) / 2, oy: (cssH - scale * (y1 + y0)) / 2 };
  st.fitScale = scale;
  st.userView = false;
};

function resize() {
  const r = $("stage").getBoundingClientRect();
  dpr = window.devicePixelRatio || 1;
  cssW = Math.max(1, Math.round(r.width));
  cssH = Math.max(1, Math.round(r.height));
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  if (!V.state.userView) V.fitView();
  V.render();
}

V.render = function () {
  const run = V.run, st = V.state, v = st.view;
  if (!run) return;
  st.tau = Math.max(0, Math.min(run.lastTick, st.tau));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = V.palette.outside;
  ctx.fillRect(0, 0, cssW, cssH);
  ctx.setTransform(dpr * v.scale, 0, 0, dpr * v.scale, dpr * v.ox, dpr * v.oy);
  const px = (n) => n / v.scale;
  V.drawMap(ctx, run, st.tau, px);
  V.drawSeasonTint(ctx, run, st.tau);
  const selBee = st.sel && st.sel.type === "bee" ? st.sel.id : null;
  st.drawn = V.drawLive(ctx, run, st.tau, px, selBee);
  if (st.sel && st.sel.type === "hornet") {
    const d = st.drawn.find((o) => o.type === "hornet" && o.id === st.sel.id);
    if (d) {
      ctx.strokeStyle = V.palette.select;
      ctx.lineWidth = px(2.2);
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r + px(5), 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  updateChrome();
};

V.requestRender = function () {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(() => { renderQueued = false; V.render(); });
};

function updateChrome() {
  const run = V.run, st = V.state, T = Math.floor(st.tau), s = V.tickState(run, T);
  const name = run.seasonNames[s.s] || "";
  const text = `${name.charAt(0).toUpperCase()}${name.slice(1)}, year ${s.y + 1}`;
  if ($("season-text").textContent !== text) {
    $("season-text").textContent = text;
    $("season-swatch").style.background = (V.seasons[name] || V.seasons.spring).swatch;
  }
  const slider = $("timeline");
  if (+slider.value !== T) slider.value = T;
  $("play").textContent = st.playing ? "Pause" : "Play";
  $("play").setAttribute("aria-label", st.playing ? "Pause" : "Play");
  V.renderPanel($("panel"), run, st.tau, st.sel);
}

let lastFrame = null;
function loop(now) {
  const st = V.state;
  if (st.playing) {
    if (lastFrame != null) st.tau += (st.speed * Math.min(100, now - lastFrame)) / 1000;
    if (st.tau >= V.run.lastTick) { st.tau = V.run.lastTick; st.playing = false; }
    lastFrame = now;
    V.render();
  } else lastFrame = null;
  requestAnimationFrame(loop);
}

V.setPlaying = function (on) {
  const st = V.state;
  if (on && st.tau >= V.run.lastTick) st.tau = 0;
  st.playing = on;
  V.requestRender();
};

function setupControls() {
  const st = V.state, slider = $("timeline");
  slider.max = V.run.lastTick;
  $("play").addEventListener("click", () => V.setPlaying(!st.playing));
  slider.addEventListener("input", () => { st.tau = +slider.value; V.requestRender(); });
  $("speed").addEventListener("change", (e) => { st.speed = +e.target.value; });
  st.speed = +$("speed").value;
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
    if (e.key === " ") { e.preventDefault(); V.setPlaying(!st.playing); }
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      st.playing = false;
      st.tau = Math.floor(st.tau) + (e.key === "ArrowRight" ? 1 : -1);
      V.requestRender();
    }
    if (e.key === "Escape") { st.sel = null; V.requestRender(); }
  });
}

function parseHash() {
  const h = location.hash.replace(/^#/, "");
  const capture = h === "capture" || h.startsWith("capture&");
  const p = new URLSearchParams(capture ? h.slice(8) : h);
  const num = (k, d) => (p.has(k) && p.get(k) !== "" && !isNaN(+p.get(k)) ? +p.get(k) : d);
  const view = p.get("view") ? p.get("view").split(",").map(Number) : null;
  return { capture, from: num("from", 0), to: num("to", null), step: num("step", 1), t: num("t", 0),
           bee: num("bee", null), hornet: num("hornet", null), view: view && view.length === 4 ? view : null };
}

V.init = async function () {
  canvas = $("map");
  ctx = canvas.getContext("2d");
  const run = (V.run = await V.loadRun(window.RUN));
  V.prepareMap(run);
  const L = run.layout, p = parseHash(), st = V.state;
  $("title").innerHTML = `Bee colony <span>${esc(L.condition || "")} condition, seed ${esc(L.seed ?? "")}</span>`;
  document.title = `Bee colony, ${L.condition || ""} seed ${L.seed ?? ""}`;
  region = p.view;
  if (p.bee != null) st.sel = { type: "bee", id: p.bee };
  else if (p.hornet != null) st.sel = { type: "hornet", id: p.hornet };
  st.tau = p.capture ? p.from : p.t;
  if (p.capture) {
    document.body.classList.add("capture");
    const to = p.to == null ? run.lastTick : p.to, step = p.step > 0 ? p.step : 1;
    window.__capture = {
      count: Math.floor((to - p.from) / step + 1e-9) + 1,
      frame(i) { st.tau = p.from + i * step; V.render(); return st.tau; },
    };
  } else {
    setupControls();
    V.setupInput(canvas);
    requestAnimationFrame(loop);
  }
  new ResizeObserver(resize).observe($("stage"));
  resize();
  $("loading").classList.add("hidden");
  window.__viewerReady = true;
};

V.init().catch((err) => {
  $("loading").textContent = `Could not load this run: ${err.message}`;
  window.__viewerError = String(err && err.stack || err);
});
