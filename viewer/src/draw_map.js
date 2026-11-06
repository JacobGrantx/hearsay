"use strict";
// The fixed world: floor, walls, hive and entrances, bloom sites, and the season tint.
// Drawn in world units (one cell = 1) under the view transform, so it stays crisp at any zoom.

V.palette = {
  outside: "#f7f2e8",
  floor: "#fdfaf3",
  wall: "#cdbfa7",
  wallEdge: "#b9aa90",
  hive: "#f5e1a8",
  hiveLine: "rgba(170, 120, 30, 0.22)",
  entrance: "#e3ad3f",
  bloomCell: "#c5e0aa",
  bloomEdge: "#7fb069",
  petal: "#ffffff",
  petalCore: "#e6a92a",
  bee: "#f2c230",
  beeEdge: "#5f440b",
  lifeTrack: "rgba(95, 68, 11, 0.16)",
  life: "#5f440b",
  lifeLow: "#d0452a",
  carry: "#3f8f3a",
  hornet: "#a9501c",
  hornetEdge: "#3f1d07",
  hornetBand: "#2b1406",
  sound1: "#14a39e",
  sound2: "#c42f97",
  sting: "#df2f27",
  sparkle: "#e9a90f",
  select: "#2e2920",
};

// Season colours: the swatch in the header, and a light wash over the map.
V.seasons = {
  spring: { swatch: "#8cc47a", tint: [120, 190, 100, 0.07] },
  summer: { swatch: "#f0c43f", tint: [250, 200, 60, 0.08] },
  autumn: { swatch: "#d9864a", tint: [214, 118, 44, 0.11] },
  winter: { swatch: "#9db3cf", tint: [110, 140, 185, 0.17] },
};

V.prepareMap = function (run) {
  const L = run.layout;
  const runs = { "#": [], H: [], E: [] };
  L.rows.forEach((row, y) => {
    let start = 0;
    for (let x = 1; x <= row.length; x++) {
      if (row[x] === row[start]) continue;
      if (runs[row[start]]) runs[row[start]].push([start, y, x - start]);
      start = x;
    }
  });
  const hive = mergeRects(runs.H);
  run.map = {
    walls: mergeRects(runs["#"]), hive, entrances: mergeRects(runs.E),
    hiveBox: hive.length ? [Math.min(...hive.map((r) => r[0])), Math.min(...hive.map((r) => r[1])),
      Math.max(...hive.map((r) => r[0] + r[2])), Math.max(...hive.map((r) => r[1] + r[3]))] : null,
  };
  // The tick at which each tick's season began, for the tint crossfade.
  run.seasonStart = new Int32Array(run.lastTick + 1);
  for (let t = 1; t <= run.lastTick; t++) {
    run.seasonStart[t] = run.ticks[t].s === run.ticks[t - 1].s ? run.seasonStart[t - 1] : t;
  }
};

V.seasonName = (run, t) => run.seasonNames[V.tickState(run, t).s] || "spring";

V.drawMap = function (ctx, run, tau, px) {
  const L = run.layout, P = V.palette, m = run.map;
  ctx.fillStyle = P.floor;
  ctx.fillRect(0, 0, L.width, L.height);

  // Hive interior with a faint comb pattern, clipped to hive cells.
  // Cells are filled as one path, so neighbouring cells show no anti-aliased seams.
  fillCells(ctx, P.hive, m.hive);
  if (m.hiveBox) {
    ctx.save();
    ctx.beginPath();
    for (const [x, y, w, h] of m.hive) ctx.rect(x, y, w, h);
    ctx.clip();
    ctx.strokeStyle = P.hiveLine;
    ctx.lineWidth = px(1);
    const [x0, y0, x1, y1] = m.hiveBox, s = 0.62, h = s * Math.sqrt(3);
    for (let row = 0, y = y0 - 1; y < y1 + 1; row++, y += h / 2) {
      for (let x = x0 - 1 + (row % 2) * 1.5 * s; x < x1 + 1; x += 3 * s) hexPath(ctx, x, y, s);
    }
    ctx.stroke();
    ctx.restore();
  }
  fillCells(ctx, P.entrance, m.entrances);

  // Walls as merged horizontal runs, with a hairline edge so corridors read clearly.
  fillCells(ctx, P.wall, m.walls);
  ctx.strokeStyle = P.wallEdge;
  ctx.lineWidth = px(1);
  ctx.beginPath();
  L.rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      if (row[x] !== "#") continue;
      if (y > 0 && L.rows[y - 1][x] !== "#") { ctx.moveTo(x, y); ctx.lineTo(x + 1, y); }
      if (y < L.height - 1 && L.rows[y + 1][x] !== "#") { ctx.moveTo(x, y + 1); ctx.lineTo(x + 1, y + 1); }
      if (x > 0 && row[x - 1] !== "#") { ctx.moveTo(x, y); ctx.lineTo(x, y + 1); }
      if (x < L.width - 1 && row[x + 1] !== "#") { ctx.moveTo(x + 1, y); ctx.lineTo(x + 1, y + 1); }
    }
  });
  ctx.stroke();

  drawBloom(ctx, run, tau, px);

  if (m.hiveBox && px(1) < 0.2) {
    const [x0, y0, x1] = m.hiveBox;
    ctx.fillStyle = "rgba(95, 68, 11, 0.75)";
    ctx.font = `600 ${px(13)}px system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText("Hive", (x0 + x1) / 2, y0 + px(6));
  }
};

function fillCells(ctx, color, rects) {
  ctx.fillStyle = color;
  ctx.beginPath();
  for (const [x, y, w, h] of rects) ctx.rect(x, y, w, h);
  ctx.fill();
}

// Merge row runs [x, y, w] into rectangles [x, y, w, h] by stacking identical runs in
// consecutive rows. Fewer shared edges means no anti-aliasing seams inside rooms and walls.
function mergeRects(runs) {
  const rows = new Map(), out = [];
  for (const [x, y, w] of runs) {
    if (!rows.has(y)) rows.set(y, []);
    rows.get(y).push([x, w]);
  }
  let open = new Map();
  for (const y of [...rows.keys()].sort((a, b) => a - b)) {
    const next = new Map();
    for (const [x, w] of rows.get(y)) {
      const k = x * 100003 + w, r = open.get(k);
      if (r && r[1] + r[3] === y) { r[3]++; next.set(k, r); }
      else { const nr = [x, y, w, 1]; out.push(nr); next.set(k, nr); }
    }
    open = next;
  }
  return out;
}

function hexPath(ctx, cx, cy, s) {
  for (let i = 0; i <= 6; i++) {
    const a = (Math.PI / 3) * i;
    const x = cx + s * Math.cos(a), y = cy + s * Math.sin(a);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
}

function drawBloom(ctx, run, tau, px) {
  const P = V.palette, name = V.seasonName(run, Math.floor(tau));
  for (const [season, cells] of Object.entries(run.layout.bloom || {})) {
    if (season === name) {
      for (const [x, y] of cells) {
        ctx.fillStyle = P.bloomCell;
        ctx.fillRect(x + 0.04, y + 0.04, 0.92, 0.92);
        flower(ctx, x + 0.5, y + 0.5, 0.3);
      }
    } else {
      // Sites out of season: a faint dashed outline, so the viewer knows where bloom returns.
      const xs = cells.map((c) => c[0]), ys = cells.map((c) => c[1]);
      ctx.save();
      ctx.strokeStyle = P.bloomEdge;
      ctx.globalAlpha = 0.45;
      ctx.lineWidth = px(1.2);
      ctx.setLineDash([px(4), px(4)]);
      ctx.strokeRect(Math.min(...xs) + 0.1, Math.min(...ys) + 0.1, Math.max(...xs) - Math.min(...xs) + 0.8, Math.max(...ys) - Math.min(...ys) + 0.8);
      ctx.restore();
    }
  }
}

function flower(ctx, cx, cy, r) {
  const P = V.palette;
  ctx.fillStyle = P.petal;
  for (let i = 0; i < 5; i++) {
    const a = (Math.PI * 2 * i) / 5 - Math.PI / 2;
    ctx.beginPath();
    ctx.arc(cx + Math.cos(a) * r * 0.55, cy + Math.sin(a) * r * 0.55, r * 0.42, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = P.petalCore;
  ctx.beginPath();
  ctx.arc(cx, cy, r * 0.3, 0, Math.PI * 2);
  ctx.fill();
}

// Season wash, crossfaded over the first ticks of a new season.
V.drawSeasonTint = function (ctx, run, tau) {
  const T = Math.max(0, Math.min(run.lastTick, Math.floor(tau)));
  const cur = V.seasons[V.seasonName(run, T)] || V.seasons.spring;
  const start = run.seasonStart[T];
  const prevName = start > 0 ? V.seasonName(run, start - 1) : null;
  const k = prevName ? Math.min(1, (tau - start) / 8) : 1;
  const prev = (prevName && V.seasons[prevName]) || cur;
  const mix = cur.tint.map((v, i) => prev.tint[i] + (v - prev.tint[i]) * k);
  ctx.fillStyle = `rgba(${mix[0]}, ${mix[1]}, ${mix[2]}, ${mix[3]})`;
  ctx.fillRect(0, 0, run.layout.width, run.layout.height);
};
