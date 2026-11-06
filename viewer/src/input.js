"use strict";
// Pointer input: tap or click selects the bee or hornet drawn under the pointer, drag pans,
// pinch and wheel zoom around the pointer, double-click refits the map.

// Nearest drawn bee or hornet whose drawn disc contains the screen point (sx, sy).
V.hitTest = function (sx, sy, slackPx) {
  const v = V.state.view;
  let best = null, bestD = Infinity;
  for (const d of V.state.drawn) {
    const dx = d.x * v.scale + v.ox - sx, dy = d.y * v.scale + v.oy - sy;
    const dist = Math.hypot(dx, dy);
    if (dist <= d.r * v.scale + slackPx && dist < bestD) { best = d; bestD = dist; }
  }
  return best;
};

V.zoomAt = function (sx, sy, factor) {
  const st = V.state, v = st.view;
  const min = st.fitScale * 0.6, max = st.fitScale * 14;
  const scale = Math.max(min, Math.min(max, v.scale * factor));
  const wx = (sx - v.ox) / v.scale, wy = (sy - v.oy) / v.scale;
  st.view = { scale, ox: sx - wx * scale, oy: sy - wy * scale };
  st.userView = true;
  V.requestRender();
};

V.setupInput = function (canvas) {
  const st = V.state, pointers = new Map();
  let moved = 0, pinch = null, multi = false;
  const local = (e) => {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const pinchInfo = () => {
    const [a, b] = [...pointers.values()];
    return { d: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
  };

  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, local(e));
    if (pointers.size === 1) { moved = 0; multi = false; }
    if (pointers.size === 2) {
      multi = true;
      const p = pinchInfo();
      pinch = { ...p, view: { ...st.view } };
    }
    canvas.classList.add("dragging");
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    const prev = pointers.get(e.pointerId), cur = local(e);
    pointers.set(e.pointerId, cur);
    if (pointers.size === 1 && !multi) {
      const dx = cur.x - prev.x, dy = cur.y - prev.y;
      moved += Math.abs(dx) + Math.abs(dy);
      if (moved > 4) {
        st.view = { ...st.view, ox: st.view.ox + dx, oy: st.view.oy + dy };
        st.userView = true;
        V.requestRender();
      }
    } else if (pointers.size === 2 && pinch) {
      // Keep the world point under the starting midpoint under the current midpoint.
      const p = pinchInfo(), v0 = pinch.view;
      const scale = Math.max(st.fitScale * 0.6, Math.min(st.fitScale * 14, v0.scale * (p.d / Math.max(1, pinch.d))));
      const wx = (pinch.mx - v0.ox) / v0.scale, wy = (pinch.my - v0.oy) / v0.scale;
      st.view = { scale, ox: p.mx - wx * scale, oy: p.my - wy * scale };
      st.userView = true;
      V.requestRender();
    }
  });

  const end = (e) => {
    if (!pointers.has(e.pointerId)) return;
    const pos = local(e);
    if (e.type === "pointerup" && pointers.size === 1 && !multi && moved <= 4) {
      const hit = V.hitTest(pos.x, pos.y, e.pointerType === "touch" ? 8 : 3);
      st.sel = hit ? { type: hit.type, id: hit.id } : null;
      V.requestRender();
    }
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) canvas.classList.remove("dragging");
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const pos = local(e), unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
    V.zoomAt(pos.x, pos.y, Math.exp(-e.deltaY * unit * 0.0015));
  }, { passive: false });

  canvas.addEventListener("dblclick", () => { V.fitView(); V.requestRender(); });

  canvas.addEventListener("pointermove", (e) => {
    if (pointers.size || e.pointerType !== "mouse") return;
    const pos = local(e);
    canvas.style.cursor = V.hitTest(pos.x, pos.y, 3) ? "pointer" : "";
  });
};
