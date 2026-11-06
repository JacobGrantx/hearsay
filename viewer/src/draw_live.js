"use strict";
// Moving things and effects at a fractional time tau. Positions are interpolated between the
// state after tick T and the state after tick T + 1; effects are pure functions of (tau - event tick),
// so any frame can be rendered on its own, in any order, with the same result.

const FX_TICKS = { sound: 6, sting: 5, hatch: 9, death: 14, delivery: 6 };
const TAU = Math.PI * 2;
const ease = (k) => 1 - (1 - k) * (1 - k);

function lerpPos(a, b, f, ix, iy) {
  if (!b) return [a[ix] + 0.5, a[iy] + 0.5];
  return [a[ix] + (b[ix] - a[ix]) * f + 0.5, a[iy] + (b[iy] - a[iy]) * f + 0.5];
}

// Hash for deterministic per-effect variation (no Math.random anywhere in rendering).
function hash(n) {
  n = Math.imul(n ^ (n >>> 16), 0x45d9f3b);
  n = Math.imul(n ^ (n >>> 16), 0x45d9f3b);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}

V.drawLive = function (ctx, run, tau, px, selected) {
  const T = Math.max(0, Math.min(run.lastTick, Math.floor(tau)));
  const f = Math.min(1, Math.max(0, tau - T));
  const P = V.palette, bf = run.bf, hf = run.hf;
  const beesA = run.ticks[T].b, beesB = V.beeMap(run, T + 1);
  const hornetsA = run.ticks[T].h, hornetsB = V.hornetMap(run, T + 1);
  const drawn = [];

  drawSounds(ctx, run, tau, px);

  // Effects under the bees: deaths fade out where the bee fell.
  for (const e of V.between(run.fx, tau - FX_TICKS.death, tau)) {
    if (e.kind !== "death") continue;
    const k = (tau - e.t) / FX_TICKS.death;
    ctx.globalAlpha = 0.7 * (1 - k);
    beeBody(ctx, e.x + 0.5, e.y + 0.5 + 0.15 * k, 0.36 * (1 - 0.3 * k), "#b9ae9c", "#857a68", px, false);
    ctx.globalAlpha = 1;
  }

  // Hornets: dark-edged diamonds, with a faint line to the bee they are chasing.
  const beeNow = V.beeMap(run, T);
  for (const h of hornetsA) {
    const [x, y] = lerpPos(h, hornetsB.get(h[hf.id]), f, hf.x, hf.y);
    const target = h[hf.target];
    if (target != null && target >= 0 && beeNow.has(target)) {
      const b = beeNow.get(target);
      ctx.strokeStyle = "rgba(169, 80, 28, 0.35)";
      ctx.lineWidth = px(1.2);
      ctx.setLineDash([px(3), px(3)]);
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(b[bf.x] + 0.5, b[bf.y] + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    hornetBody(ctx, x, y, 0.46, px);
    drawn.push({ type: "hornet", id: h[hf.id], x, y, r: 0.46 });
  }

  // Bees: warm yellow, a thin ring for life left out of the cap, a green dot when carrying.
  for (const b of beesA) {
    const id = b[bf.id];
    const [x, y] = lerpPos(b, beesB.get(id), f, bf.x, bf.y);
    const stunned = b[bf.stunned] > 0;
    const r = 0.34;
    if (id === selected) selectionMarks(ctx, run, b, x, y, r, px);
    beeBody(ctx, x, y, r, P.bee, stunned ? P.sting : P.beeEdge, px, true);
    const life = b[bf.life], frac = Math.max(0, Math.min(1, life / run.lifeCap));
    const low = life < 0.25 * (run.layout.base_life || 250);
    ctx.lineWidth = Math.max(px(1.6), 0.07);
    ctx.strokeStyle = P.lifeTrack;
    ctx.beginPath();
    ctx.arc(x, y, r + 0.12, 0, TAU);
    ctx.stroke();
    ctx.strokeStyle = low ? P.lifeLow : P.life;
    ctx.beginPath();
    ctx.arc(x, y, r + 0.12, -Math.PI / 2, -Math.PI / 2 + TAU * frac);
    ctx.stroke();
    if (b[bf.carrying]) {
      ctx.fillStyle = P.carry;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = px(1.2);
      ctx.beginPath();
      ctx.arc(x + 0.3, y - 0.3, 0.15, 0, TAU);
      ctx.fill();
      ctx.stroke();
    }
    drawn.push({ type: "bee", id, x, y, r: r + 0.12 });
  }

  // Effects over the bees: sting flashes, hatch sparkles, delivery pulses.
  for (const e of V.between(run.fx, tau - FX_TICKS.hatch, tau)) {
    const age = tau - e.t;
    if (e.kind === "sting" && age < FX_TICKS.sting) stingFlash(ctx, run, e, age / FX_TICKS.sting, px);
    if (e.kind === "hatch" && age < FX_TICKS.hatch) sparkle(ctx, e, age / FX_TICKS.hatch);
    if (e.kind === "delivery" && age < FX_TICKS.delivery) {
      const b = V.beeMap(run, e.t).get(e.bee);
      if (!b) continue;
      const k = age / FX_TICKS.delivery;
      ctx.strokeStyle = `rgba(233, 169, 15, ${0.9 * (1 - k)})`;
      ctx.lineWidth = px(2.5);
      ctx.beginPath();
      ctx.arc(b[bf.x] + 0.5, b[bf.y] + 0.5, 0.5 + 1.6 * ease(k), 0, TAU);
      ctx.stroke();
    }
  }
  return drawn;
};

function beeBody(ctx, x, y, r, fill, edge, px, stripes) {
  ctx.fillStyle = fill;
  ctx.strokeStyle = edge;
  ctx.lineWidth = Math.max(px(1.2), 0.05);
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  if (stripes && r / px(1) > 7) {
    ctx.save();
    ctx.clip();
    ctx.fillStyle = "rgba(60, 40, 5, 0.55)";
    ctx.fillRect(x - r * 0.2, y - r, r * 0.22, 2 * r);
    ctx.fillRect(x + r * 0.28, y - r, r * 0.22, 2 * r);
    ctx.restore();
  }
  ctx.stroke();
}

function hornetBody(ctx, x, y, r, px) {
  const P = V.palette;
  ctx.beginPath();
  ctx.moveTo(x, y - r);
  ctx.lineTo(x + r, y);
  ctx.lineTo(x, y + r);
  ctx.lineTo(x - r, y);
  ctx.closePath();
  ctx.fillStyle = P.hornet;
  ctx.fill();
  ctx.save();
  ctx.clip();
  ctx.fillStyle = P.hornetBand;
  ctx.fillRect(x - r, y - r * 0.12, 2 * r, r * 0.24);
  ctx.restore();
  ctx.strokeStyle = P.hornetEdge;
  ctx.lineWidth = Math.max(px(1.3), 0.05);
  ctx.stroke();
}

function selectionMarks(ctx, run, b, x, y, r, px) {
  const P = V.palette, L = run.layout, v = L.vision || 4;
  ctx.strokeStyle = "rgba(46, 41, 32, 0.35)";
  ctx.lineWidth = px(1);
  ctx.setLineDash([px(4), px(3)]);
  ctx.strokeRect(b[run.bf.x] - v, b[run.bf.y] - v, 2 * v + 1, 2 * v + 1);
  const goTo = /^go_to:(-?\d+),(-?\d+)$/.exec(b[run.bf.intent] || "");
  if (goTo) {
    const gx = +goTo[1] + 0.5, gy = +goTo[2] + 0.5;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(gx, gy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.lineWidth = px(2);
    ctx.strokeStyle = P.select;
    ctx.beginPath();
    ctx.moveTo(gx - 0.3, gy - 0.3); ctx.lineTo(gx + 0.3, gy + 0.3);
    ctx.moveTo(gx + 0.3, gy - 0.3); ctx.lineTo(gx - 0.3, gy + 0.3);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  ctx.strokeStyle = P.select;
  ctx.lineWidth = px(2.2);
  ctx.beginPath();
  ctx.arc(x, y, r + 0.12 + px(5), 0, TAU);
  ctx.stroke();
}

function drawSounds(ctx, run, tau, px) {
  const P = V.palette, radius = run.layout.hearing || 10;
  for (const s of V.between(run.sounds, tau - FX_TICKS.sound, tau)) {
    const k = (tau - s.t) / FX_TICKS.sound;
    const color = s.sound === "sound-2" ? P.sound2 : P.sound1;
    const x = s.x + 0.5, y = s.y + 0.5;
    ctx.globalAlpha = 0.05 * (1 - k);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = color;
    for (const lag of [0, 0.18]) {
      const kk = Math.max(0, Math.min(1, (k - lag) / 0.7));
      if (kk <= 0 || kk >= 1) continue;
      ctx.globalAlpha = 0.75 * (1 - kk);
      ctx.lineWidth = px(2.4);
      ctx.beginPath();
      ctx.arc(x, y, 0.4 + (radius - 0.4) * ease(kk), 0, TAU);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
}

function stingFlash(ctx, run, e, k, px) {
  const x = e.x + 0.5, y = e.y + 0.5, h = V.hornetMap(run, e.t).get(e.hornet);
  ctx.strokeStyle = V.palette.sting;
  ctx.globalAlpha = 1 - k;
  if (h) {
    ctx.lineWidth = px(2.5);
    ctx.beginPath();
    ctx.moveTo(h[run.hf.x] + 0.5, h[run.hf.y] + 0.5);
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
  ctx.beginPath();
  ctx.arc(x, y, 0.35 + 0.6 * ease(k), 0, TAU);
  ctx.fill();
  ctx.lineWidth = px(2.2);
  ctx.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = (TAU * i) / 8 + 0.2, r0 = 0.45 + 0.5 * ease(k), r1 = r0 + 0.45;
    ctx.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0);
    ctx.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
}

function sparkle(ctx, e, k) {
  const x = e.x + 0.5, y = e.y + 0.5, n = e.queen ? 8 : 6;
  ctx.globalAlpha = 1 - k;
  for (let i = 0; i < n; i++) {
    const a = TAU * (i / n + hash(e.bee * 31 + i) * 0.15) + k * 1.2;
    const d = 0.35 + 1.1 * ease(k) * (0.7 + 0.5 * hash(e.bee * 17 + i));
    star(ctx, x + Math.cos(a) * d, y + Math.sin(a) * d, 0.2 * (1 - 0.5 * k), i % 2 ? "#ffffff" : V.palette.sparkle);
  }
  ctx.globalAlpha = 1;
}

function star(ctx, x, y, r, color) {
  ctx.fillStyle = color;
  ctx.strokeStyle = "rgba(150, 100, 0, 0.6)";
  ctx.lineWidth = r * 0.15;
  ctx.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI / 4) * i, rr = i % 2 ? r * 0.35 : r;
    ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}
