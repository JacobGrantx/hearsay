"use strict";
// The side panel: the colony at a glance, or the selected bee's life, decisions and memories.

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const DIR_WORDS = { N: "north", NE: "north-east", E: "east", SE: "south-east", S: "south", SW: "south-west", W: "west", NW: "north-west" };
const TRIGGER_WORDS = {
  timer: "regular check", stung: "after a sting", hornet: "saw a hornet", bloom: "saw bloom",
  sound: "heard a sound", arrived: "arrived", home: "entered the hive", life50: "life fell below half",
  life25: "life fell below a quarter", hatched: "just hatched",
};
// What the AI bees read instead of bee, hive, hornet and bloom (src/digital_life/vocab.py). The viewer stays human-facing.
const AGENTS_SEE = {
  abstract: "Agents see: units, zone O, K entities, G cells, signals A and B.",
  neutral: "Agents see: members, home, moving things, bright cells, sound-1 and sound-2.",
};
const MODE_WORDS = { chase: "Chasing", sound: "Following a sound", ambush: "Waiting in ambush", wander: "Wandering" };
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

V.intentWords = function (intent, direction, target) {
  if (!intent) return "No decision yet";
  const [kind, arg] = intent.split(":");
  if (kind === "explore") return `Exploring ${DIR_WORDS[arg || direction] || "onward"}`;
  if (kind === "go_to") {
    const xy = arg ? arg.split(",") : target || [];
    return xy.length === 2 ? `Going to ${xy[0]}, ${xy[1]}` : "Going to a spot";
  }
  return { go_home: "Going home", flee: "Fleeing", wait: "Waiting" }[kind] || cap(kind.replace(/_/g, " "));
};

function soundTag(sound) {
  if (sound === "sound-1") return '<span class="tag s1">sound 1</span>';
  if (sound === "sound-2") return '<span class="tag s2">sound 2</span>';
  return "";
}

const LEGEND = `
<ul class="legend">
  <li><svg width="22" height="22"><circle cx="11" cy="11" r="6" fill="#f2c230" stroke="#5f440b" stroke-width="1.2"/><path d="M11 3 A8 8 0 1 1 3.4 13.5" fill="none" stroke="#5f440b" stroke-width="1.6"/></svg>Bee, ring shows life left</li>
  <li><svg width="22" height="22"><circle cx="9" cy="12" r="6" fill="#f2c230" stroke="#5f440b" stroke-width="1.2"/><circle cx="15.5" cy="6" r="3" fill="#3f8f3a" stroke="#fff" stroke-width="1.2"/></svg>Bee carrying from bloom</li>
  <li><svg width="22" height="22"><path d="M11 2 L20 11 L11 20 L2 11 Z" fill="#a9501c" stroke="#3f1d07" stroke-width="1.3"/><rect x="2" y="10" width="18" height="2.2" fill="#2b1406"/></svg>Hornet</li>
  <li><svg width="22" height="22"><rect x="2" y="2" width="18" height="18" rx="2" fill="#c5e0aa"/><circle cx="11" cy="11" r="4" fill="#fff"/><circle cx="11" cy="11" r="1.8" fill="#e6a92a"/></svg>Bloom</li>
  <li><svg width="22" height="22"><circle cx="11" cy="11" r="8" fill="none" stroke="#14a39e" stroke-width="2.4"/></svg>Sound 1</li>
  <li><svg width="22" height="22"><circle cx="11" cy="11" r="8" fill="none" stroke="#c42f97" stroke-width="2.4"/></svg>Sound 2</li>
  <li><svg width="22" height="22"><g stroke="#df2f27" stroke-width="2.2"><path d="M11 1v5M11 16v5M1 11h5M16 11h5M4 4l3.5 3.5M14.5 14.5L18 18M18 4l-3.5 3.5M7.5 14.5L4 18"/></g></svg>Sting</li>
</ul>`;

V.renderPanel = function (el, run, tau, sel) {
  const T = Math.max(0, Math.min(run.lastTick, Math.floor(tau)));
  const key = `${T}|${sel ? sel.type + sel.id : ""}`;
  if (el.dataset.key === key) return;
  el.dataset.key = key;
  if (sel && sel.type === "bee") el.innerHTML = beeHTML(run, T, sel.id);
  else if (sel && sel.type === "hornet") el.innerHTML = hornetHTML(run, T, sel.id);
  else el.innerHTML = colonyHTML(run, T);
  if (document.body.classList.contains("capture")) fitPanel(el);
};

// Video frames cannot scroll: drop the oldest items from the longest list until the panel fits.
function fitPanel(el) {
  const lists = [...el.querySelectorAll("ul[data-list]")];
  for (let guard = 0; guard < 60 && el.scrollHeight > el.clientHeight; guard++) {
    const longest = lists.filter((u) => u.children.length > 1).sort((a, b) => b.children.length - a.children.length)[0];
    if (!longest) break;
    longest.lastElementChild.remove();
  }
}

function colonyHTML(run, T) {
  const st = run.ticks[T], start = run.seasonStart[T];
  const c = V.countEvents(run, start, T);
  return `
  <h2>The colony</h2>
  <p class="muted">Click or tap a bee to follow its decisions and memories.</p>
  <h3>Right now</h3>
  <div class="stats"><span>Bees alive</span><span>${st.b.length}</span><span>Hornets on the map</span><span>${st.h.length}</span></div>
  <h3>This season so far</h3>
  <div class="stats"><span>Deliveries</span><span>${c.delivery}</span><span>Stings</span><span>${c.sting}</span>
  <span>Hatchings</span><span>${c.hatch}</span><span>Deaths</span><span>${c.death}</span></div>
  <h3>Key</h3>${LEGEND}${AGENTS_SEE[run.vocab] ? `<p class="muted">${AGENTS_SEE[run.vocab]}</p>` : ""}`;
}

function beeHTML(run, T, id) {
  const h = run.bees.get(id) || { decisions: [], heard: [], stings: [], deliveries: [] };
  const b = V.beeMap(run, T).get(id), bf = run.bf;
  let status, life = 0;
  if (b) {
    life = b[bf.life];
    const cell = run.layout.rows[b[bf.y]][b[bf.x]];
    const parts = [cell === "H" || cell === "E" ? "in the hive" : "out in the maze"];
    if (b[bf.carrying]) parts.push("carrying");
    if (b[bf.stunned] > 0) parts.push("stunned");
    status = `Alive, ${parts.join(", ")}`;
  } else if (h.died != null && h.died <= T) status = `Died at tick ${h.died}`;
  else status = "Not hatched yet";
  const pct = Math.max(0, Math.min(100, (100 * life) / run.lifeCap));
  const low = life < 0.25 * (run.layout.base_life || 250);
  const born = h.born != null ? `Hatched at tick ${h.born}${h.cause === "start" ? ", a founder" : h.cause === "queen" ? ", by the queen" : ""}.` : "";
  const stings = h.stings.filter((e) => e.t <= T).length, deliveries = h.deliveries.filter((e) => e.t <= T).length;
  const decisions = h.decisions.filter((d) => d.t <= T).slice(-6).reverse();
  const memoryOff = run.layout.condition === "no_memory";
  const beliefs = h.decisions.filter((d) => d.t <= T && d.remember).slice(-12).reverse();
  const heard = h.heard.filter((e) => e.t <= T).slice(-4).reverse();
  return `
  <h2>Bee ${esc(id)}</h2>
  <p class="muted">${esc(status)}</p>
  ${b ? `<div class="lifebar${low ? " low" : ""}"><div style="width:${pct.toFixed(1)}%"></div></div>
  <p>Life ${Math.round(life)} of ${run.lifeCap}. ${esc(V.intentWords(b[bf.intent]))}.</p>` : ""}
  <p class="muted">${born} Stung ${stings} ${stings === 1 ? "time" : "times"}, ${deliveries} ${deliveries === 1 ? "delivery" : "deliveries"}.</p>
  <h3>Recent decisions</h3>
  ${decisions.length ? `<ul data-list="decisions">${decisions.map((d, i) => decisionHTML(d, i === 0)).join("")}</ul>` : '<p class="muted">None yet.</p>'}
  <h3>What it remembers</h3>
  ${memoryOff ? '<p class="muted">Memory is switched off in this run.</p>'
    : beliefs.length ? `<ul data-list="beliefs">${beliefs.map((d) => `<li><span class="quote">${esc(d.remember)}</span> <span class="when">tick ${d.t}</span></li>`).join("")}</ul>`
    : '<p class="muted">Nothing written yet.</p>'}
  <h3>Heard at home</h3>
  ${heard.length ? `<ul data-list="heard">${heard.map((e) => `<li><span class="quote">${esc(e.text)}</span> <span class="when">bee ${esc(e.from)}, tick ${e.t}</span></li>`).join("")}</ul>` : '<p class="muted">Nothing yet.</p>'}`;
}

function decisionHTML(d, latest) {
  const intent = V.intentWords(d.intent === "go_to" && d.target ? `go_to:${d.target[0]},${d.target[1]}` : d.intent, d.direction, d.target);
  const extra = [];
  if (d.remember) extra.push(`<div>Remember: <span class="quote">${esc(d.remember)}</span></div>`);
  if (d.say) extra.push(`<div>Says: <span class="quote">${esc(d.say)}</span></div>`);
  return `<li${latest ? ' class="latest"' : ""}><div class="when">tick ${d.t}, ${esc(TRIGGER_WORDS[d.trigger] || d.trigger || "")}</div>
  <div>${esc(intent)} ${soundTag(d.sound)}</div>${extra.join("")}</li>`;
}

function hornetHTML(run, T, id) {
  const h = V.hornetMap(run, T).get(id), hf = run.hf;
  if (!h) return `<h2>Hornet ${esc(id)}</h2><p class="muted">Not on the map now.</p>`;
  const gene = (name) => `<span>${cap(name)}</span><span>${h[hf[name]]} of 10</span>`;
  const target = h[hf.target], mode = h[hf.mode];
  const doing = mode === "chase" && target >= 0 ? `Chasing bee ${target}` : MODE_WORDS[mode] || cap(String(mode || ""));
  return `
  <h2>Hornet ${esc(id)}</h2>
  <p class="muted">${esc(doing)}.</p>
  <h3>Genes</h3>
  <div class="stats">${gene("smell")}${gene("hearing")}${gene("ambush")}</div>
  <p class="muted" style="margin-top:12px">${run.layout.condition === "frozen_hornets"
    ? "Hornets have no mind. In this run their genes are frozen at the first draw."
    : "Hornets have no mind. Their genes evolve: at fixed intervals outside winter the least fit hornet is replaced by a copy of one picked in proportion to fitness, sometimes mutated."}</p>`;
}
