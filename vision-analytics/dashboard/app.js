const $ = (sel) => document.querySelector(sel);
let lastInsights = [];
let lastSummary = { by_type: {}, by_camera: {}, total: 0 };

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

function camCard(cam, extra = "") {
  const live = cam.alive ? "ok" : "crit";
  const mods = (cam.modules || []).map((m) => `<span class="badge">${m}</span>`).join("");
  return `<article class="card ${cam.fire && cam.fire.active ? "pulse" : ""}">
    <img src="/api/stream/${cam.id}.mjpeg" alt="${cam.name}" />
    <div class="meta">
      <strong>${cam.name}</strong>
      <div>${mods}<span class="badge ${live}">${cam.alive ? "live" : "down"}</span></div>
      <p class="muted">${cam.id} · decode ${cam.decoded_fps || 0} fps · ${cam.processed || 0} frames</p>
      ${extra}
    </div>
  </article>`;
}

function insightCard(item) {
  const ev = item.evidence || {};
  const bits = Object.entries(ev)
    .slice(0, 6)
    .map(([k, v]) => `${k.replaceAll("_", " ")}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" · ");
  return `<article class="insight ${item.severity || "info"}">
    <span class="badge ${item.severity === "action" ? "crit" : item.severity === "watch" ? "warn" : "ok"}">${item.domain} · ${item.severity}</span>
    <h3>${item.title}</h3>
    <p>${item.recommendation}</p>
    ${bits ? `<p class="meta-line">${bits}</p>` : ""}
  </article>`;
}

function renderInsights(list, selector) {
  const el = $(selector);
  if (!el) return;
  const items = list || [];
  el.innerHTML = items.length ? items.map(insightCard).join("") : `<p class="muted">Waiting for accumulated events…</p>`;
}

function renderBars(counts, selector, clsFor) {
  const el = $(selector);
  if (!el) return;
  const entries = Object.entries(counts || {});
  if (!entries.length) {
    el.innerHTML = `<p class="muted">No events stored yet.</p>`;
    return;
  }
  const max = Math.max(...entries.map(([, n]) => n), 1);
  el.innerHTML = entries
    .sort((a, b) => b[1] - a[1])
    .map(([label, n]) => {
      const cls = clsFor ? clsFor(label) : "";
      return `<div class="bar-row ${cls}"><span>${label}</span><div class="track"><div class="fill" style="width:${(n / max) * 100}%"></div></div><strong>${n}</strong></div>`;
    })
    .join("");
}

function setEngine(engine) {
  if (!engine) return;
  $("#kpi-fps").textContent = engine.fps != null ? engine.fps.toFixed(1) : "—";
  $("#kpi-target").textContent = engine.target_fps ?? 90;
  $("#kpi-batch").textContent = engine.avg_batch_size != null ? engine.avg_batch_size.toFixed(1) : "—";
  $("#kpi-queue").textContent = engine.queue_depth ?? "—";
  $("#kpi-device").textContent = engine.device || "—";
  $("#kpi-fps").style.color = engine.meeting_target ? "var(--ok)" : "var(--warn)";
}

function applyInsights(insights, summary) {
  lastInsights = insights || lastInsights;
  lastSummary = summary || lastSummary;
  const action = lastInsights.filter((i) => i.severity === "action").slice(0, 3);
  renderInsights(action.length ? action : lastInsights.slice(0, 3), "#overview-insights");
  renderInsights(lastInsights, "#insight-board");
  renderInsights(lastInsights.filter((i) => i.domain === "store"), "#store-insights");
  renderInsights(lastInsights.filter((i) => i.domain === "traffic"), "#traffic-insights");
  renderInsights(lastInsights.filter((i) => i.domain === "fire"), "#fire-insights");
  renderBars(lastSummary.by_type, "#type-bars", (t) => {
    if (t.includes("wrong")) return "wrong";
    if (t.includes("jump") || t.includes("fire")) return "jump";
    if (t.includes("people")) return "people";
    return "";
  });
  renderBars(lastSummary.by_camera, "#cam-bars");
}

function render(cameras) {
  $("#camera-grid").innerHTML = cameras.map((c) => camCard(c)).join("") || "<p class='muted'>No cameras enabled.</p>";

  const store = cameras.filter((c) => c.store);
  const inC = store.reduce((s, c) => s + (c.store.in_count || 0), 0);
  const outC = store.reduce((s, c) => s + (c.store.out_count || 0), 0);
  const occ = store.reduce((s, c) => s + (c.store.occupancy || 0), 0);
  $("#store-kpis").innerHTML = `
    <div class="chip"><span>In</span><strong>${inC}</strong></div>
    <div class="chip"><span>Out</span><strong>${outC}</strong></div>
    <div class="chip"><span>Occupancy</span><strong>${occ}</strong></div>
    <div class="chip"><span>Net</span><strong>${inC - outC}</strong></div>`;
  $("#store-cams").innerHTML = store.map((c) => camCard(c, `<p>in ${c.store.in_count} · out ${c.store.out_count} · occ ${c.store.occupancy}</p>`)).join("");
  $("#heatmaps").innerHTML = store.map((c) => `<div><p>${c.name}</p><img src="/api/heatmap/${c.id}.jpg?t=${Date.now()}" alt="heatmap ${c.id}" /></div>`).join("");

  const traffic = cameras.filter((c) => c.traffic);
  const crossed = traffic.reduce((s, c) => s + (c.traffic.vehicles_crossed || 0), 0);
  const wrong = traffic.reduce((s, c) => s + (c.traffic.wrong_way || 0), 0);
  const jumps = traffic.reduce((s, c) => s + (c.traffic.signal_jumps || 0), 0);
  $("#traffic-kpis").innerHTML = `
    <div class="chip"><span>Crossed signal</span><strong>${crossed}</strong></div>
    <div class="chip"><span>Wrong way</span><strong>${wrong}</strong></div>
    <div class="chip"><span>Signal jumps</span><strong>${jumps}</strong></div>`;
  $("#traffic-cams").innerHTML = traffic.map((c) => camCard(c, `<p>signal <b>${c.traffic.signal_color}</b> · crossed ${c.traffic.vehicles_crossed} · wrong ${c.traffic.wrong_way} · jumps ${c.traffic.signal_jumps}</p>`)).join("");

  const fire = cameras.filter((c) => c.fire);
  const fires = fire.reduce((s, c) => s + (c.fire.fire_count || 0), 0);
  const smokes = fire.reduce((s, c) => s + (c.fire.smoke_count || 0), 0);
  $("#fire-kpis").innerHTML = `
    <div class="chip"><span>Fire boxes</span><strong>${fires}</strong></div>
    <div class="chip"><span>Smoke boxes</span><strong>${smokes}</strong></div>`;
  $("#fire-cams").innerHTML = fire.map((c) => camCard(c, `<p>${c.fire.active ? "ALERT" : "clear"} · fire ${c.fire.fire_count} · smoke ${c.fire.smoke_count}</p>`)).join("");
}

function eventDetail(e) {
  if (e.type === "people_count") return `${e.kind || "cross"} · in ${e.in_count} / out ${e.out_count} · occupancy ${e.occupancy}`;
  if (e.type === "vehicle_crossing") return `${e.label || "vehicle"} crossed · total ${e.total} · signal ${e.signal || "n/a"}`;
  if (e.type === "wrong_way") return `${e.label || "vehicle"} against flow (dot ${e.dot})`;
  if (e.type === "signal_jump") return `${e.label || "vehicle"} ran ${e.signal || "red"}`;
  if (e.type === "fire_smoke_alert") return `${e.kind} · conf ${e.confidence} · fire ${e.fire_count} smoke ${e.smoke_count}`;
  return JSON.stringify(e).slice(0, 180);
}

async function loadEvents() {
  const type = $("#event-filter").value;
  const qs = type ? `?type=${encodeURIComponent(type)}&limit=300` : "?limit=300";
  const rows = await fetch(`/api/events${qs}`).then((r) => r.json());
  $("#event-rows").innerHTML = rows.map((e) => {
    const when = new Date((e.ts || 0) * 1000).toLocaleString();
    return `<tr><td>${when}</td><td>${e.camera_id || ""}</td><td class="event-type">${e.type}</td><td>${eventDetail(e)}</td></tr>`;
  }).join("");
  const counts = {};
  rows.forEach((e) => {
    counts[e.type] = (counts[e.type] || 0) + 1;
  });
  $("#event-stats").innerHTML = Object.entries(counts)
    .map(([k, v]) => `<div class="chip"><span>${k}</span><strong>${v}</strong></div>`)
    .join("") || `<div class="chip"><span>Events</span><strong>0</strong></div>`;
}

$("#refresh-events").addEventListener("click", loadEvents);
$("#event-filter").addEventListener("change", loadEvents);

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
  ws.onmessage = (msg) => {
    const payload = JSON.parse(msg.data);
    if (payload.engine) setEngine(payload.engine);
    if (payload.cameras) render(payload.cameras);
    if (payload.insights || payload.summary) applyInsights(payload.insights, payload.summary);
    if (payload.kind === "event") loadEvents();
  };
  ws.onclose = () => setTimeout(connect, 1500);
}

fetch("/api/cameras").then((r) => r.json()).then(render).catch(() => {});
fetch("/api/engine").then((r) => r.json()).then(setEngine).catch(() => {});
fetch("/api/insights").then((r) => r.json()).then((d) => applyInsights(d.insights, d.summary)).catch(() => {});
loadEvents();
connect();
