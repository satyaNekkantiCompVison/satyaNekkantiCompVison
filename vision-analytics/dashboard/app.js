const $ = (sel) => document.querySelector(sel);

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

function setEngine(engine) {
  if (!engine) return;
  $("#kpi-fps").textContent = engine.fps != null ? engine.fps.toFixed(1) : "—";
  $("#kpi-target").textContent = engine.target_fps ?? 90;
  $("#kpi-batch").textContent = engine.avg_batch_size != null ? engine.avg_batch_size.toFixed(1) : "—";
  $("#kpi-queue").textContent = engine.queue_depth ?? "—";
  $("#kpi-device").textContent = engine.device || "—";
  $("#kpi-fps").style.color = engine.meeting_target ? "var(--ok)" : "var(--warn)";
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

async function loadEvents() {
  const type = $("#event-filter").value;
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  const rows = await fetch(`/api/events${qs}`).then((r) => r.json());
  $("#event-rows").innerHTML = rows.map((e) => {
    const when = new Date((e.ts || 0) * 1000).toLocaleString();
    const detail = JSON.stringify(e, null, 0).slice(0, 240);
    return `<tr><td>${when}</td><td>${e.camera_id || ""}</td><td>${e.type}</td><td><code>${detail}</code></td></tr>`;
  }).join("");
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
    if (payload.kind === "event") loadEvents();
  };
  ws.onclose = () => setTimeout(connect, 1500);
}

fetch("/api/cameras").then((r) => r.json()).then(render).catch(() => {});
fetch("/api/engine").then((r) => r.json()).then(setEngine).catch(() => {});
loadEvents();
connect();
