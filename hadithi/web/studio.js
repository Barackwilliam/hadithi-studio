/* Hadithi Studio Pro: ukurasa wa kitaalamu unaoongea na /api/hs/* */
"use strict";

const S = {
  h: null,                 // hali kutoka kwa seva
  view: localStorage.getItem("hs-view") || "andika",
  miradi: [],
  kazi: null,              // kazi inayoendelea
  dockWazi: true,
  drawer: null,            // {aina: "mhusika"|"tukio", id}
  chatBusy: false,
  vo: { kichwa: true, manukuu: true },
};

const NAV = [
  { id: "andika", ico: "💬", jina: "Andika", step: 1 },
  { id: "wahusika", ico: "👥", jina: "Wahusika", step: 2 },
  { id: "storyboard", ico: "🎞️", jina: "Storyboard", step: 3 },
  { id: "video", ico: "🎬", jina: "Video", step: 4 },
  { id: "mipangilio", ico: "⚙️", jina: "Mipangilio" },
];
const SAUTI = {
  rehema: ["Rehema", "Mwanamke · Tanzania"], zuri: ["Zuri", "Mwanamke · Kenya"],
  daudi: ["Daudi", "Mwanamume · Tanzania"], rafiki: ["Rafiki", "Mwanamume · Kenya"],
};
const MIENDO = [["auto", "Otomatiki"], ["karibia", "Karibia"], ["mbali", "Mbali"], ["kulia", "Kulia →"], ["kushoto", "← Kushoto"], ["tuli", "Tuli"]];
const MAWAZO = [
  "Niandikie hadithi ya katuni ya watoto kuhusu sungura mjanja na fisi mlafi, matukio 6",
  "Tamthiliya ya kifamilia: mama anayepambana kumsomesha mwanawe, matukio 8, kwa YouTube",
  "Hadithi fupi ya kuchekesha kwa TikTok kuhusu fundi simu na mteja wake msumbufu",
  "Nina mpango wa series ya episode 10. Nitakupa muhtasari wake, kisha anza na Episode 1",
  "Hadithi ya mapenzi ya kijijini yenye funzo, kwa mtindo wa anime",
];
const UCHAWI = ["Fanya iwe usiku wenye mbalamwezi", "Ongeza mvua", "Wafanye watabasamu", "Badilisha mandhari kuwa ufukweni",
  "Mvalishe nguo nyekundu", "Ongeza mwanga wa jua la asubuhi", "Fanya picha iwe ya kuvutia zaidi"];
const AINA_YA_KAZI = { chora: "Inachora picha", hariri: "Inahariri picha ✨", katuni: "Inageuza picha kuwa katuni", video: "Inatengeneza video" };

/* ------------------------------------------------------------------ vifaa */
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>");
const H = () => S.h.hadithi;
const wahusika = () => Object.entries(H().wahusika || {}).filter(([k]) => k !== "msimulizi");
const jina = (id) => (id === "msimulizi" ? "Msimulizi" : (H().wahusika?.[id]?.jina || id));
const pichaW = (id) => S.h.picha.wahusika[id];
const pichaT = (n) => S.h.picha.matukio[String(n)];
const ar = () => ({ "9:16": "ar-916", "1:1": "ar-11" }[H().ukubwa] || "ar-169");
const sautiKey = (v) => (SAUTI[v] ? v : Object.keys(SAUTI).find((k) => String(v || "").toLowerCase().includes(k)) || "daudi");
const hz = (v) => parseInt(String(v || "0").replace(/[^0-9+-]/g, "")) || 0;
const dakika = (s) => (s < 60 ? `${Math.max(1, Math.round(s))}s` : `${Math.round(s / 60)} dk`);

async function api(path, { method = "GET", body, form } = {}) {
  const opts = { method, headers: {} };
  if (form) { opts.body = form; opts.method = "POST"; }
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.method = method === "GET" ? "POST" : method; opts.headers["Content-Type"] = "application/json"; }
  const r = await fetch(path, opts);
  let data = null;
  try { data = await r.json(); } catch { /* si json */ }
  if (!r.ok) throw new Error((data && (data.detail || data.kosa)) || `Hitilafu ${r.status}`);
  return data;
}

function toast(ujumbe, aina = "info", ms = 4200) {
  const t = document.createElement("div");
  t.className = `toast ${aina}`;
  t.innerHTML = ujumbe;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), ms);
}
const kosa = (e) => toast(`⚠️ ${esc(e.message || e)}`, "bad", 7000);

/* ------------------------------------------------------------------ hali */
async function pakia() {
  S.h = await api("/api/hs/hali");
  shell();
  await render();
  if (S.drawer) fungua_drawer(S.drawer.aina, S.drawer.id, true);
  const k = S.h.kazi?.[0];
  if (k && !S.kazi) fuatilia(k);
}

function shell() {
  $("#jina-la-mradi").textContent = H().kichwa || S.h.mradi;
  document.title = `${H().kichwa} · Hadithi Studio`;
  const gpu = $("#pill-gpu"), ai = $("#pill-ai");
  gpu.className = `pill gpu ${S.h.mfumo.gpu ? "ok" : "warn"}`;
  gpu.lastChild.textContent = S.h.mfumo.gpu ? "GPU tayari" : (S.h.mfumo.picha === "mtandao" ? "Picha za mtandao" : "Hakuna GPU");
  ai.className = `pill ${S.h.mfumo.gemini ? "ok" : "warn"}`;
  ai.lastChild.textContent = S.h.mfumo.gemini ? "Gemini" : "Gemini: weka key";
  const imekamilika = {
    andika: (H().matukio || []).length > 1 || S.h.chat.length > 1,
    wahusika: wahusika().length > 0 && wahusika().every(([k]) => pichaW(k)),
    storyboard: (H().matukio || []).every((_, i) => pichaT(i + 1)),
    video: S.h.video.length > 0,
  };
  $("#nav-side").innerHTML = NAV.map((n) => `
    <button class="nav-item ${S.view === n.id ? "active" : ""}" data-go="${n.id}">
      <span class="ico">${n.ico}</span>${n.jina}
      ${imekamilika[n.id] ? '<span class="check">✓</span>' : n.step ? `<span class="step">${n.step}</span>` : ""}
    </button>`).join("") + `
    <div class="nav-foot">
      <b style="color:var(--text)">${esc(H().kichwa)}</b><br>
      ${(H().matukio || []).length} matukio · ${wahusika().length} wahusika · ${esc(H().ukubwa)}
      ${S.h.mfululizo ? `<br>📺 Episode ${S.h.mfululizo.episode}` : ""}
    </div>`;
  $("#nav-bottom").innerHTML = NAV.map((n) => `
    <button class="${S.view === n.id ? "active" : ""}" data-go="${n.id}"><span class="ico">${n.ico}</span>${n.jina}</button>`).join("");
}

async function enda(view) {
  if (S.drawer || $("#tabaka").innerHTML) funga();
  S.view = view;
  if (view !== "miradi") localStorage.setItem("hs-view", view);
  shell();
  await render();
  window.scrollTo({ top: 0 });
}

async function render() {
  const main = $("#main");
  const V = { miradi: vMiradi, andika: vAndika, wahusika: vWahusika, storyboard: vStoryboard, video: vVideo, mipangilio: vMipangilio };
  main.innerHTML = await (V[S.view] || vAndika)();
  if (S.view === "andika") { const m = $("#msgs"); if (m) m.scrollTop = m.scrollHeight; }
}

/* ------------------------------------------------------------------ miradi */
async function vMiradi() {
  S.miradi = (await api("/api/hs/miradi")).miradi;
  return `
  <section class="hero">
    <h1>Kila hadithi inastahili <em>kuonekana.</em></h1>
    <p>Andika wazo lako. AI inaunda wahusika, inachora kila tukio, inawapa sauti za Kiswahili, kisha inakuletea video ya tamthiliya au katuni.</p>
    <div class="actions">
      <button class="btn primary lg" data-act="mradi-mpya">✨ Anza hadithi mpya</button>
      <button class="btn lg" data-act="mradi-mfano">📖 Jaribu hadithi ya mfano</button>
    </div>
  </section>
  <div class="view-head"><div><h1>Hadithi zako</h1><p>Chagua hadithi ili kuendelea pale ulipoishia.</p></div></div>
  <div class="grid">
    <div class="card project new" data-act="mradi-mpya"><div><div class="plus">+</div><b>Hadithi mpya</b><br><small>Anza kutoka mwanzo</small></div></div>
    ${S.miradi.map((m) => `
      <div class="card project" data-act="mradi-chagua" data-jina="${esc(m.jina)}">
        <div class="cover" style="${m.jalada ? `background-image:url('${m.jalada}')` : ""}">${m.jalada ? "" : "📖"}</div>
        <div class="meta"><b>${esc(m.kichwa)}</b>
          <small>${m.matukio} matukio · ${m.wahusika} wahusika · ${esc(m.ukubwa)}${m.video ? " · 🎬" : ""}</small></div>
        ${m.jina === S.h.mradi ? '<span class="badge acc" style="position:absolute;top:8px;left:8px">Sasa</span>' : ""}
        <button class="btn sm del" data-act="mradi-futa" data-jina="${esc(m.jina)}" title="Futa">🗑️</button>
      </div>`).join("")}
  </div>`;
}

function modal_mradi_mpya() {
  const mitindo = Object.keys(S.h.mitindo);
  tabaka(`
    <div class="scrim" data-act="funga"></div>
    <div class="modal">
      <h2>Hadithi mpya ✨</h2><p class="muted" style="margin-top:0">Unaweza kubadilisha haya yote baadaye.</p>
      <div class="stack">
        <label class="field">Kichwa cha hadithi<input type="text" id="mp-kichwa" placeholder="Mfano: Sungura Mjanja" autofocus></label>
        <div class="field">Ukubwa wa video
          <div class="opt-grid" id="mp-ukubwa">
            ${[["16:9", "YouTube", 34, 20], ["9:16", "TikTok / Reels", 18, 32], ["1:1", "Instagram", 26, 26]].map(([v, l, w, h], i) => `
              <button class="opt ${i === 0 ? "on" : ""}" data-v="${v}" data-act="chagua-opt"><div class="shape" style="width:${w}px;height:${h}px"></div>${v}<br><small class="muted">${l}</small></button>`).join("")}
          </div></div>
        <div class="field">Mtindo wa picha
          <div class="style-grid" id="mp-mtindo">
            ${mitindo.map((m, i) => `<button class="opt ${i === 0 ? "on" : ""}" data-v="${esc(m)}" data-act="chagua-opt">${esc(m)}</button>`).join("")}
          </div></div>
        <div class="actions" style="justify-content:flex-end">
          <button class="btn ghost" data-act="funga">Ghairi</button>
          <button class="btn primary" data-act="unda-mradi">Unda hadithi →</button>
        </div>
      </div>
    </div>`);
  setTimeout(() => $("#mp-kichwa")?.focus(), 50);
}

/* ------------------------------------------------------------------ andika (chat) */
async function vAndika() {
  const ms = S.h.chat;
  const t = H().matukio || [];
  const thumbs = t.slice(0, 6).map((_, i) => `<div style="${pichaT(i + 1) ? `background-image:url('${pichaT(i + 1)}')` : ""}"></div>`).join("");
  return `
  <div class="view-head"><div><h1>Andika hadithi</h1><p>Ongea na AI kama na mwandishi mwenzako. Hadithi inahifadhiwa yenyewe.</p></div>
    <div class="actions"><button class="btn sm ghost" data-act="chat-futa">🗑️ Anza upya mazungumzo</button></div></div>
  ${S.h.mfumo.gemini ? "" : `<div class="card pad" style="margin-bottom:14px;border-color:var(--warn)">🔑 Chat inahitaji API key ya Gemini (bure).
      <a href="#" data-go="mipangilio">Iweke kwenye Mipangilio →</a> Unaweza pia kuandika hadithi mwenyewe kwenye <a href="#" data-go="storyboard">Storyboard</a>.</div>`}
  <div class="chat-wrap">
    <div class="card chat">
      <div class="msgs" id="msgs">
        ${ms.map((m) => `<div class="msg ${m.role === "user" ? "user" : "assistant"}">${m.role === "user" ? "" : '<div class="who">Mwandishi AI</div>'}${md(m.content)}</div>`).join("")}
        ${S.chatBusy ? '<div class="msg assistant typing"><span></span><span></span><span></span></div>' : ""}
      </div>
      ${ms.length <= 1 ? `<div class="chips">${MAWAZO.map((w) => `<button class="chip" data-act="wazo">${esc(w)}</button>`).join("")}</div>` : ""}
      <div class="composer">
        <textarea id="ujumbe" rows="1" placeholder="Andika wazo lako au ombi la mabadiliko… (Enter kutuma)"></textarea>
        <button class="btn primary" data-act="tuma" ${S.chatBusy ? "disabled" : ""}>Tuma ➤</button>
      </div>
    </div>
    <aside class="chat-side">
      <div class="card pad story-peek">
        <small class="faint">HADITHI YA SASA</small>
        <h3>${esc(H().kichwa)}</h3>
        <div class="mini">${thumbs}</div>
        <div class="stat"><span class="muted">Matukio</span><b>${t.length}</b></div>
        <div class="stat"><span class="muted">Wahusika</span><b>${wahusika().length}</b></div>
        <div class="stat"><span class="muted">Mwendo wa AI</span><b>${t.filter((x) => x.mwendo_ai).length}</b></div>
        <div class="stat"><span class="muted">Ukubwa</span><b>${esc(H().ukubwa)}</b></div>
        <button class="btn primary" style="width:100%;margin-top:12px" data-go="storyboard">Fungua Storyboard →</button>
      </div>
    </aside>
  </div>`;
}

async function tuma(maandishi) {
  const ujumbe = (maandishi ?? $("#ujumbe")?.value ?? "").trim();
  if (!ujumbe || S.chatBusy) return;
  S.chatBusy = true;
  S.h.chat.push({ role: "user", content: ujumbe });
  await render();
  try {
    const r = await api("/api/hs/chat", { body: { ujumbe } });
    S.chatBusy = false;
    await pakia();
    if (r.imesasishwa) toast(`✅ Hadithi imesasishwa. <a href="#" data-go="storyboard">Fungua Storyboard →</a>`, "ok", 6000);
  } catch (e) {
    S.chatBusy = false;
    S.h.chat.push({ role: "assistant", content: `⚠️ ${e.message}` });
    await render();
  }
}

/* ------------------------------------------------------------------ wahusika */
async function vWahusika() {
  const w = wahusika();
  const m = H().wahusika?.msimulizi || {};
  return `
  <div class="view-head"><div><h1>Wahusika</h1><p>Kila mhusika huchorwa mara moja. Picha yake hutumika kuhakikisha sura inafanana kwenye kila tukio.</p></div>
    <div class="actions">
      <button class="btn" data-act="mhusika-mpya">➕ Mhusika mpya</button>
      <button class="btn primary" data-act="chora" data-aina="wahusika">🎨 Chora wahusika</button>
    </div></div>
  <div class="chars">
    <div class="card char narrator" data-act="mhusika" data-id="msimulizi">
      <div class="portrait">🎙️</div>
      <div class="info"><b>Msimulizi</b><small>Sauti: ${esc(SAUTI[sautiKey(m.sauti)][0])}</small></div>
    </div>
    ${w.map(([id, x]) => `
      <div class="card char" data-act="mhusika" data-id="${esc(id)}">
        <div class="portrait" style="${pichaW(id) ? `background-image:url('${pichaW(id)}')` : ""}">${pichaW(id) ? "" : "👤"}
          ${pichaW(id) ? "" : '<span class="badge">Haijachorwa</span>'}</div>
        <div class="info"><b>${esc(x.jina || id)}</b><small>${esc(x.maelezo || "Hakuna maelezo")}</small></div>
      </div>`).join("")}
    <div class="card char scene add" data-act="mhusika-mpya"><div><div style="font-size:30px">＋</div>Ongeza mhusika</div></div>
  </div>`;
}

function dMhusika(id) {
  const mpya = !id;
  const x = mpya ? { sauti: "rehema" } : (H().wahusika[id] || {});
  const ni_msimulizi = id === "msimulizi";
  const p = id && pichaW(id);
  const matoleo = S.h.matoleo[`mhusika:${id}`] || 0;
  return `
  <div class="drawer-head"><h2>${mpya ? "Mhusika mpya" : ni_msimulizi ? "🎙️ Msimulizi" : esc(x.jina || id)}</h2>
    <button class="icon-btn" data-act="funga">✕</button></div>
  <div class="drawer-body">
    ${ni_msimulizi || mpya ? "" : `
      <div class="media portrait" style="${p ? `background-image:url('${p}')` : ""}">${p ? "" : "👤 Bado hajachorwa"}</div>
      <div class="media-tools">
        <button class="btn sm" data-act="chora-upya-mhusika" data-id="${esc(id)}">🔁 Chora upya</button>
        <button class="btn sm" data-act="pakia" data-lengo="mhusika" data-id="${esc(id)}" data-geuza="ndiyo">✨ Picha yangu → Katuni</button>
        <button class="btn sm" data-act="pakia" data-lengo="mhusika" data-id="${esc(id)}" data-geuza="hapana">📷 Pakia picha</button>
        ${matoleo ? `<button class="btn sm" data-act="rudisha" data-lengo="mhusika" data-id="${esc(id)}">↩️ Rudisha (${matoleo})</button>` : ""}
      </div>
      ${p ? uchawi("mhusika", id) : ""}`}
    ${ni_msimulizi ? "" : `
      <label class="field">Jina<input type="text" id="m-jina" value="${esc(x.jina || "")}" placeholder="Mfano: Neema"></label>
      <label class="field">Sura yake <span class="hint">Kwa Kiingereza: umri, nywele, nguo, rangi. Mfano: "a 9 year old girl, braided hair, yellow dress"</span>
        <textarea id="m-maelezo" rows="3">${esc(x.maelezo || "")}</textarea></label>`}
    <div class="field">Sauti
      <div class="voice-grid" id="m-sauti">
        ${Object.entries(SAUTI).map(([k, [n, d]]) => `<button class="voice ${sautiKey(x.sauti) === k ? "on" : ""}" data-v="${k}" data-act="chagua-opt"><b>${n}</b><small>${d}</small></button>`).join("")}
      </div></div>
    <div class="row">
      <label class="field">Kina cha sauti: <span id="mkinav">${hz(x.kina)}</span>Hz <span class="hint">+ mtoto · − mzee</span>
        <input type="range" id="m-kina" min="-40" max="40" step="5" value="${hz(x.kina)}" oninput="mkinav.textContent=this.value"></label>
      <label class="field">Kasi: <span id="mkasiv">${hz(x.kasi)}</span>%
        <input type="range" id="m-kasi" min="-40" max="40" step="5" value="${hz(x.kasi)}" oninput="mkasiv.textContent=this.value"></label>
    </div>
    <div><button class="btn sm" data-act="sikiliza">🔊 Sikiliza sauti</button> <audio id="m-audio" style="vertical-align:middle;height:34px;max-width:220px" class="hidden" controls></audio></div>
  </div>
  <div class="drawer-foot">
    <button class="btn primary" data-act="hifadhi-mhusika" data-id="${esc(id || "")}">💾 Hifadhi</button>
    ${mpya || ni_msimulizi ? "" : `<button class="btn danger ghost" data-act="futa-mhusika" data-id="${esc(id)}" style="margin-left:auto">🗑️ Futa</button>`}
  </div>`;
}

function uchawi(lengo, id) {
  return `
  <div class="magic">
    <h4>✨ Hariri kwa maneno <small class="muted" style="font-weight:500">kama Nano Banana</small></h4>
    <div class="row" style="flex-direction:row">
      <input type="text" id="agizo" placeholder="Mfano: mvalishe kofia nyekundu" style="flex:1">
      <button class="btn primary" data-act="hariri" data-lengo="${lengo}" data-id="${esc(id)}">Badilisha</button>
    </div>
    <div class="seg">${UCHAWI.map((u) => `<button class="chip" data-act="agizo">${esc(u)}</button>`).join("")}</div>
    <small class="faint">${S.h.mfumo.gemini ? "Inatumia Gemini kwanza; ikishindikana inatumia GPU." : "Bila key ya Gemini, inatumia GPU ya Colab."} Toleo la awali huhifadhiwa: ↩️ Rudisha.</small>
  </div>`;
}

/* ------------------------------------------------------------------ storyboard */
async function vStoryboard() {
  const t = H().matukio || [];
  const hakuna = t.filter((_, i) => !pichaT(i + 1)).length;
  return `
  <div class="view-head"><div><h1>Storyboard</h1><p>${t.length} matukio · ${hakuna ? `${hakuna} bado hayajachorwa` : "picha zote ziko tayari ✓"}. Bonyeza tukio ili kulihariri.</p></div>
    <div class="actions">
      <button class="btn" data-act="tukio-ongeza">➕ Tukio</button>
      <button class="btn primary" data-act="chora" data-aina="yote">🎨 ${hakuna ? "Chora picha" : "Chora zilizobadilika"}</button>
    </div></div>
  ${S.h.kosa ? `<div class="card pad" style="border-color:var(--bad);margin-bottom:14px">⚠️ ${esc(S.h.kosa)}</div>` : ""}
  <div class="board ${H().ukubwa === "9:16" ? "tall" : ""}">
    ${t.map((x, i) => {
      const n = i + 1, p = pichaT(n);
      const m = (x.mazungumzo || [])[0];
      const mstari = !m ? '<span class="faint">Hakuna mazungumzo</span>' : typeof m === "string" ? esc(m)
        : `<b>${esc(jina(Object.keys(m)[0]))}:</b> ${esc(Object.values(m)[0])}`;
      return `
      <div class="card scene" data-act="tukio" data-id="${n}">
        <div class="thumb ${ar()}" style="${p ? `background-image:url('${p}')` : ""}">${p ? "" : "🎨 Bado haijachorwa"}
          <span class="badge num">${n}</span>
          <span class="tags">${x.mwendo_ai ? '<span class="badge ai">🎥 AI</span>' : ""}${x.mwendo && x.mwendo !== "auto" ? `<span class="badge">${esc(x.mwendo)}</span>` : ""}</span>
        </div>
        <div class="body">
          <div class="line">${mstari}</div>
          <div class="avatars">${(x.wahusika || []).map((w) => `<span title="${esc(jina(w))}" style="${pichaW(w) ? `background-image:url('${pichaW(w)}')` : ""}">${pichaW(w) ? "" : esc(jina(w)[0] || "?")}</span>`).join("")}</div>
        </div>
      </div>`;
    }).join("")}
    <div class="card scene add ${ar()}" data-act="tukio-ongeza"><div><div style="font-size:30px">＋</div>Ongeza tukio</div></div>
  </div>`;
}

function dTukio(n) {
  const x = H().matukio[n - 1];
  if (!x) return "";
  const p = pichaT(n);
  const matoleo = S.h.matoleo[`tukio:${n}`] || 0;
  const mistari = (x.mazungumzo || []).map((m) => (typeof m === "string" ? { msemaji: "msimulizi", maneno: m }
    : { msemaji: Object.keys(m)[0], maneno: Object.values(m)[0] }));
  const wasemaji = [["msimulizi", "🎙️ Msimulizi"], ...wahusika().map(([k, v]) => [k, v.jina || k])];
  return `
  <div class="drawer-head"><h2>Tukio ${n} <small class="faint">/ ${H().matukio.length}</small></h2>
    <button class="icon-btn" data-act="tukio-hamisha" data-id="${n}" data-mw="-1" title="Sogeza juu">↑</button>
    <button class="icon-btn" data-act="tukio-hamisha" data-id="${n}" data-mw="1" title="Sogeza chini">↓</button>
    <button class="icon-btn" data-act="funga">✕</button></div>
  <div class="drawer-body">
    <div class="media ${ar()}" style="${p ? `background-image:url('${p}')` : ""}">${p ? "" : "🎨 Bado haijachorwa"}</div>
    <div class="media-tools">
      <button class="btn sm" data-act="chora-upya-tukio" data-id="${n}">${p ? "🔁 Chora upya" : "🎨 Chora"}</button>
      <button class="btn sm" data-act="pakia" data-lengo="tukio" data-id="${n}" data-geuza="hapana">📷 Tumia picha yangu</button>
      ${matoleo ? `<button class="btn sm" data-act="rudisha" data-lengo="tukio" data-id="${n}">↩️ Rudisha (${matoleo})</button>` : ""}
    </div>
    ${p ? uchawi("tukio", n) : ""}
    <label class="field">Picha ya tukio <span class="hint">Kwa Kiingereza: mahali, kitendo, hisia, mwanga</span>
      <textarea id="t-picha" rows="3">${esc(x.picha || "")}</textarea></label>
    <div class="field">Wanaoonekana kwenye picha
      <div class="seg" id="t-wahusika">${wahusika().map(([k, v]) => `<button class="${(x.wahusika || []).includes(k) ? "on" : ""}" data-v="${esc(k)}" data-act="geuza-on">${esc(v.jina || k)}</button>`).join("") || '<span class="faint">Hakuna wahusika bado</span>'}</div></div>
    <div class="field">Mwendo wa kamera
      <div class="seg" id="t-mwendo">${MIENDO.map(([v, l]) => `<button class="${(x.mwendo || "auto") === v ? "on" : ""}" data-v="${v}" data-act="chagua-seg">${l}</button>`).join("")}</div></div>
    <label class="switch"><input type="checkbox" id="t-ai" ${x.mwendo_ai ? "checked" : ""}><span class="track"></span>
      <span class="lbl"><b>🎥 Mwendo wa AI</b><small>Wahusika na mazingira wasogee kweli. Inahitaji GPU, na huchukua dakika 3 hadi 6.</small></span></label>
    <div class="field">Mazungumzo
      <div class="lines" id="t-mistari">${mistari.map((m) => mstariEd(m, wasemaji)).join("")}</div>
      <button class="btn sm ghost" data-act="mstari-ongeza" style="align-self:flex-start">＋ Ongeza mstari</button></div>
  </div>
  <div class="drawer-foot">
    <button class="btn primary" data-act="hifadhi-tukio" data-id="${n}">💾 Hifadhi</button>
    <button class="btn danger ghost" data-act="tukio-futa" data-id="${n}" style="margin-left:auto">🗑️ Futa tukio</button>
  </div>`;
}

function mstariEd(m, wasemaji) {
  return `<div class="line-ed">
    <select>${wasemaji.map(([k, l]) => `<option value="${esc(k)}" ${k === m.msemaji ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>
    <textarea rows="2" placeholder="Maneno…">${esc(m.maneno)}</textarea>
    <button class="btn sm ghost x" data-act="mstari-futa" title="Ondoa">✕</button></div>`;
}

/* ------------------------------------------------------------------ video */
async function vVideo() {
  const t = H().matukio || [];
  const ai = t.filter((x) => x.mwendo_ai).length;
  const hakuna = t.filter((_, i) => !pichaT(i + 1)).length;
  const mp = H().mipangilio || {};
  const muda = hakuna * 8 + ai * 270 + t.length * 12 + 20;
  const v = S.h.video[0];
  return `
  <div class="view-head"><div><h1>Video</h1><p>Unganisha picha, mwendo, sauti, manukuu na muziki kuwa video moja.</p></div>
    <div class="actions">
      <a class="btn sm ghost" href="/api/hs/pakua/hadithi">📤 Pakua hadithi (.yaml)</a>
      <button class="btn sm" data-act="episode">📺 Episode inayofuata</button>
    </div></div>
  <div class="video-wrap">
    <div class="stack">
      <div class="player">${v ? `<video src="${v.url}" controls playsinline></video>` : `<div style="padding:40px;text-align:center">🎬<br>Video yako itaonekana hapa</div>`}</div>
      ${v ? `<div class="actions"><a class="btn primary" href="${v.url}" download="${esc(v.jina)}">⬇️ Pakua video (${v.mb} MB)</a></div>` : ""}
      ${S.h.video.length > 1 ? `<div class="card pad history"><b>Video za awali</b>${S.h.video.slice(1).map((x) => `<a href="${x.url}" target="_blank"><span>🎞️ ${esc(x.jina)}</span><span class="muted">${x.mb} MB</span></a>`).join("")}</div>` : ""}
    </div>
    <div class="cta stack">
      <div><b style="font-size:18px">Tengeneza video</b>
        <div class="estimate">
          <span class="pill">🎞️ ${t.length} matukio</span><span class="pill">🎥 ${ai} AI</span>
          ${hakuna ? `<span class="pill warn"><span class="dot"></span>${hakuna} picha mpya</span>` : ""}
          <span class="pill">⏱️ ~${dakika(muda)}</span></div></div>
      <label class="switch"><input type="checkbox" id="vo-kichwa" ${S.vo.kichwa ? "checked" : ""} data-act="vo"><span class="track"></span><span class="lbl"><b>Kadi ya kichwa</b><small>Jina la hadithi mwanzoni</small></span></label>
      <label class="switch"><input type="checkbox" id="vo-manukuu" ${S.vo.manukuu ? "checked" : ""} data-act="vo"><span class="track"></span><span class="lbl"><b>Manukuu</b><small>Maneno chini ya video</small></span></label>
      <label class="switch"><input type="checkbox" id="vo-kina" ${mp.kina_2_5d !== false ? "checked" : ""} data-act="mp-kina"><span class="track"></span><span class="lbl"><b>Mwendo wa kina (2.5D)</b><small>Picha zisizo na AI zipate kina</small></span></label>
      <label class="field">Nguvu ya mwendo wa AI: <span id="nmv">${mp.nguvu_ya_mwendo ?? 127}</span>
        <input type="range" min="40" max="220" step="10" value="${mp.nguvu_ya_mwendo ?? 127}" id="vo-nguvu" oninput="nmv.textContent=this.value"></label>
      <div class="field">🎵 Muziki wa nyuma
        ${S.h.muziki ? `<audio src="${S.h.muziki}" controls style="width:100%;height:36px"></audio>
          <button class="btn sm ghost" data-act="muziki-ondoa">Ondoa muziki</button>`
          : `<div><button class="btn sm" data-act="muziki">⬆️ Pakia muziki (mp3)</button></div><span class="hint">Muziki wa bure: <a href="https://pixabay.com/music/" target="_blank">pixabay.com/music</a></span>`}</div>
      <button class="btn primary lg" data-act="video" ${S.kazi ? "disabled" : ""}>🎬 Tengeneza video</button>
      ${ai && !S.h.mfumo.gpu ? '<small class="faint">⚠️ Hakuna GPU: matukio ya AI yatapata mwendo wa kina badala yake.</small>' : ""}
    </div>
  </div>`;
}

/* ------------------------------------------------------------------ mipangilio */
async function vMipangilio() {
  const mp = H().mipangilio || {};
  const mitindo = S.h.mitindo;
  return `
  <div class="view-head"><div><h1>Mipangilio</h1><p>Muonekano wa hadithi, AI na ubora.</p></div></div>
  <div class="stack" style="max-width:820px">
    <div class="card pad stack">
      <b>🔑 Gemini (Chat na kuhariri picha)</b>
      <p class="muted" style="margin:0">Bure: fungua <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com/apikey</a>, bonyeza <b>Create API key</b>, kisha ibandike hapa.</p>
      <div class="row" style="flex-direction:row"><input type="password" id="key" placeholder="${S.h.mfumo.gemini ? "✅ Key imewekwa (bandika mpya kuibadilisha)" : "AIza…"}">
        <button class="btn" data-act="key">Hifadhi</button></div>
    </div>
    <div class="card pad stack">
      <b>📖 Hadithi</b>
      <label class="field">Kichwa<input type="text" id="s-kichwa" value="${esc(H().kichwa)}"></label>
      <div class="field">Ukubwa wa video
        <div class="seg" id="s-ukubwa">${[["16:9", "YouTube 16:9"], ["9:16", "TikTok 9:16"], ["1:1", "Instagram 1:1"]].map(([v, l]) => `<button class="${H().ukubwa === v ? "on" : ""}" data-v="${v}" data-act="chagua-seg">${l}</button>`).join("")}</div></div>
      <div class="field">Mtindo wa picha
        <div class="style-grid">${Object.entries(mitindo).map(([k, v]) => `<button class="opt ${H().mtindo === v ? "on" : ""}" data-act="mtindo" data-v="${esc(v)}">${esc(k)}</button>`).join("")}</div>
        <textarea id="s-mtindo" rows="2">${esc(H().mtindo)}</textarea></div>
      <div><button class="btn primary" data-act="hifadhi-msingi">💾 Hifadhi</button></div>
    </div>
    <div class="card pad stack">
      <b>🎛️ Ubora</b>
      <label class="field">Sura za wahusika zifanane: <span id="nmm">${mp.nguvu_ya_mhusika ?? 0.5}</span> <span class="hint">Juu = zinafanana zaidi; chini = picha inafuata maelezo zaidi</span>
        <input type="range" min="0.2" max="0.8" step="0.05" id="s-nguvu" value="${mp.nguvu_ya_mhusika ?? 0.5}" oninput="nmm.textContent=this.value"></label>
      <label class="switch"><input type="checkbox" id="s-jina" ${mp.onyesha_jina ? "checked" : ""}><span class="track"></span><span class="lbl"><b>Jina la msemaji kwenye manukuu</b><small>"Neema: Habari!"</small></span></label>
      <label class="field">Mbegu (seed) <span class="hint">Badilisha ili upate picha tofauti kabisa</span><input type="number" id="s-mbegu" value="${mp.mbegu ?? 42}"></label>
      <div><button class="btn primary" data-act="hifadhi-ubora">💾 Hifadhi</button></div>
    </div>
    <details class="card pad"><summary><b>🧑‍💻 Hadithi kamili (YAML)</b> <span class="muted">kwa wataalamu</span></summary>
      <div class="stack" style="margin-top:12px"><textarea id="s-yaml" rows="16" style="font-family:ui-monospace,monospace;font-size:13px">${esc(await (await fetch("/api/hs/pakua/hadithi", { cache: "no-store" })).text())}</textarea>
      <div class="actions"><button class="btn" data-act="hifadhi-yaml">💾 Tumia YAML hii</button><a class="btn ghost" href="/api/hs/pakua/hadithi">📤 Pakua</a></div></div></details>
    <div class="card pad"><b>🖥️ Mfumo</b><div class="muted" style="margin-top:6px">Picha: ${esc(S.h.mfumo.picha)} · Sauti: ${esc(S.h.mfumo.sauti)} · GPU: ${S.h.mfumo.gpu ? "ndiyo ✅" : "hapana"} · Mradi: ${esc(S.h.mradi)}</div></div>
  </div>`;
}

/* ------------------------------------------------------------------ tabaka (drawer/modal) */
function tabaka(html) { $("#tabaka").innerHTML = html; }
function funga() { tabaka(""); S.drawer = null; }
function fungua_drawer(aina, id, kimya = false) {
  S.drawer = { aina, id };
  const ndani = aina === "mhusika" ? dMhusika(id) : dTukio(Number(id));
  if (!ndani) return funga();
  if (kimya && $(".drawer")) { $(".drawer").innerHTML = ndani; return; }
  tabaka(`<div class="scrim" data-act="funga"></div><div class="drawer">${ndani}</div>`);
}

/* ------------------------------------------------------------------ kazi ndefu */
async function anzisha(ahadi) {
  try {
    const k = await ahadi;
    fuatilia(k);
  } catch (e) { kosa(e); }
}

function fuatilia(k) {
  S.kazi = k;
  dock();
  clearTimeout(S._poll);
  const zunguka = async () => {
    try {
      const x = await api(`/api/hs/kazi/${k.id}`);
      S.kazi = x;
      dock();
      if (x.hali === "imekamilika" || x.hali === "imeshindwa") {
        S.kazi = null;
        if (x.hali === "imekamilika") toast(`✅ ${AINA_YA_KAZI[x.aina] || "Kazi"}: imekamilika (${dakika(x.sekunde)})`, "ok");
        else toast(`⚠️ ${esc(x.kosa || "Imeshindikana")}`, "bad", 10000);
        setTimeout(() => { if (!S.kazi) $("#dock").classList.add("hidden"); }, x.hali === "imeshindwa" ? 12000 : 2500);
        await pakia();
        if (x.aina === "video" && x.hali === "imekamilika" && S.view !== "video") enda("video");
        return;
      }
    } catch { /* jaribu tena */ }
    S._poll = setTimeout(zunguka, 1500);
  };
  zunguka();
}

function dock() {
  const d = $("#dock"), k = S.kazi;
  if (!k) return;
  d.classList.remove("hidden");
  const imekwisha = k.hali === "imekamilika" || k.hali === "imeshindwa";
  d.innerHTML = `
    <div class="dock-head" data-act="dock">
      ${imekwisha ? (k.hali === "imekamilika" ? "✅" : "⚠️") : '<div class="spinner"></div>'}
      <b>${AINA_YA_KAZI[k.aina] || "Kazi"}${k.hali === "inasubiri" ? " (kwenye foleni)" : ""}</b>
      <span class="muted" style="font-size:12px">${dakika(k.sekunde || 0)}</span><span class="faint">${S.dockWazi ? "▾" : "▴"}</span>
    </div>
    ${imekwisha ? "" : '<div class="bar"><i></i></div>'}
    ${S.dockWazi ? `<div class="dock-log" id="dock-log">${esc((k.log || []).slice(-12).join("\n") || "Inaanza…")}${k.kosa ? `\n⚠️ ${esc(k.kosa)}` : ""}</div>` : ""}`;
  const log = $("#dock-log");
  if (log) log.scrollTop = log.scrollHeight;
}

/* ------------------------------------------------------------------ vitendo */
function chaguaFaili(accept) {
  return new Promise((ok) => {
    const i = document.createElement("input");
    i.type = "file"; i.accept = accept;
    i.onchange = () => ok(i.files[0] || null);
    i.click();
  });
}
const thamani = (sel) => $(`${sel} .on`)?.dataset.v;

const ACT = {
  "funga": () => funga(),
  "dock": () => { S.dockWazi = !S.dockWazi; dock(); },
  "chagua-opt": (el) => { el.parentElement.querySelectorAll(".on").forEach((x) => x.classList.remove("on")); el.classList.add("on"); },
  "chagua-seg": (el) => ACT["chagua-opt"](el),
  "geuza-on": (el) => el.classList.toggle("on"),

  // miradi
  "mradi-mpya": () => modal_mradi_mpya(),
  "unda-mradi": async () => {
    const kichwa = $("#mp-kichwa").value.trim() || "Hadithi Mpya";
    try {
      await api("/api/hs/mradi/mpya", { body: { kichwa, ukubwa: thamani("#mp-ukubwa"), mtindo: thamani("#mp-mtindo") } });
      funga(); await pakia(); enda("andika"); toast("✨ Hadithi mpya imeundwa. Anza kwa kuiambia AI wazo lako!", "ok");
    } catch (e) { kosa(e); }
  },
  "mradi-chagua": async (el, ev) => {
    if (ev.target.closest(".del")) return;
    try { await api("/api/hs/mradi/chagua", { body: { jina: el.dataset.jina } }); await pakia(); enda("storyboard"); } catch (e) { kosa(e); }
  },
  "mradi-futa": async (el) => {
    if (!confirm("Futa hadithi hii pamoja na picha na video zake zote? Haiwezi kurudishwa.")) return;
    try { await api("/api/hs/mradi/futa", { body: { jina: el.dataset.jina } }); await pakia(); enda("miradi"); } catch (e) { kosa(e); }
  },
  "mradi-mfano": async () => { try { await api("/api/hs/mradi/mfano", { body: {} }); await pakia(); enda("storyboard"); } catch (e) { kosa(e); } },
  "episode": async () => {
    if (!confirm("Unda episode inayofuata? Wahusika, sura zao na sauti zao vitabaki vile vile.")) return;
    try { await api("/api/hs/mradi/episode", { body: {} }); await pakia(); enda("andika"); toast("📺 Episode mpya iko tayari. Iambie AI kinachotokea!", "ok"); } catch (e) { kosa(e); }
  },

  // chat
  "tuma": () => tuma(),
  "wazo": (el) => { const t = $("#ujumbe"); t.value = el.textContent; t.focus(); },
  "chat-futa": async () => { if (confirm("Anza mazungumzo upya? Hadithi yenyewe haitafutwa.")) { await api("/api/hs/chat/futa", { body: {} }); await pakia(); } },

  // wahusika
  "mhusika": (el) => fungua_drawer("mhusika", el.dataset.id),
  "mhusika-mpya": () => fungua_drawer("mhusika", null),
  "hifadhi-mhusika": async (el) => {
    const body = { id: el.dataset.id || null, jina: $("#m-jina")?.value || "", maelezo: $("#m-maelezo")?.value || "",
      sauti: thamani("#m-sauti") || "daudi", kina: +$("#m-kina").value, kasi: +$("#m-kasi").value };
    try { const r = await api("/api/hs/mhusika", { body }); S.drawer = { aina: "mhusika", id: r.id }; await pakia(); toast("💾 Imehifadhiwa", "ok"); } catch (e) { kosa(e); }
  },
  "futa-mhusika": async (el) => {
    if (!confirm("Futa mhusika huyu? Maneno yake yatabaki kama ya msimulizi.")) return;
    try { await api("/api/hs/mhusika/futa", { body: { id: el.dataset.id } }); funga(); await pakia(); } catch (e) { kosa(e); }
  },
  "sikiliza": async (el) => {
    el.disabled = true; el.textContent = "⏳ …";
    try {
      const j = $("#m-jina")?.value;
      const r = await api("/api/hs/sauti/jaribu", { body: { sauti: thamani("#m-sauti"), kina: +$("#m-kina").value, kasi: +$("#m-kasi").value,
        maneno: j ? `Habari! Jina langu ni ${j}. Karibu kwenye hadithi yetu.` : "Hapo zamani za kale, palikuwa na kijiji kimoja kizuri." } });
      const a = $("#m-audio"); a.src = r.url; a.classList.remove("hidden"); a.play();
    } catch (e) { kosa(e); }
    el.disabled = false; el.textContent = "🔊 Sikiliza sauti";
  },
  "chora-upya-mhusika": (el) => anzisha(api("/api/hs/kazi/chora", { body: { aina: "wahusika", upya_wahusika: [el.dataset.id] } })),

  // matukio
  "tukio": (el) => fungua_drawer("tukio", el.dataset.id),
  "tukio-ongeza": async () => {
    try { const r = await api("/api/hs/tukio/ongeza", { body: { baada_ya: (H().matukio || []).length } }); await pakia(); fungua_drawer("tukio", r.namba); } catch (e) { kosa(e); }
  },
  "tukio-hamisha": async (el) => {
    try { const r = await api("/api/hs/tukio/hamisha", { body: { namba: +el.dataset.id, mwelekeo: +el.dataset.mw } }); S.drawer = { aina: "tukio", id: r.namba }; await pakia(); } catch (e) { kosa(e); }
  },
  "tukio-futa": async (el) => {
    if (!confirm(`Futa tukio ${el.dataset.id}?`)) return;
    try { await api("/api/hs/tukio/futa", { body: { namba: +el.dataset.id } }); funga(); await pakia(); } catch (e) { kosa(e); }
  },
  "mstari-ongeza": () => {
    const wasemaji = [["msimulizi", "🎙️ Msimulizi"], ...wahusika().map(([k, v]) => [k, v.jina || k])];
    $("#t-mistari").insertAdjacentHTML("beforeend", mstariEd({ msemaji: "msimulizi", maneno: "" }, wasemaji));
    $("#t-mistari").lastElementChild.querySelector("textarea").focus();
  },
  "mstari-futa": (el) => el.closest(".line-ed").remove(),
  "hifadhi-tukio": async (el) => {
    const mistari = [...document.querySelectorAll("#t-mistari .line-ed")].map((r) => ({ msemaji: r.querySelector("select").value, maneno: r.querySelector("textarea").value }));
    const body = { namba: +el.dataset.id, picha: $("#t-picha").value, wahusika: [...document.querySelectorAll("#t-wahusika .on")].map((b) => b.dataset.v),
      mwendo: thamani("#t-mwendo") || "auto", mwendo_ai: $("#t-ai").checked, mistari };
    try { await api("/api/hs/tukio", { body }); await pakia(); toast("💾 Tukio limehifadhiwa", "ok"); } catch (e) { kosa(e); }
  },
  "chora-upya-tukio": (el) => anzisha(api("/api/hs/kazi/chora", { body: { aina: "matukio", upya_matukio: pichaT(el.dataset.id) ? [+el.dataset.id] : [] } })),
  "chora": (el) => anzisha(api("/api/hs/kazi/chora", { body: { aina: el.dataset.aina } })),

  // picha: uchawi, pakia, rudisha
  "agizo": (el) => { $("#agizo").value = el.textContent; $("#agizo").focus(); },
  "hariri": (el) => {
    const agizo = $("#agizo").value.trim();
    if (!agizo) return toast("Andika unachotaka kibadilike, au chagua pendekezo.", "warn");
    anzisha(api("/api/hs/kazi/hariri", { body: { lengo: el.dataset.lengo, id: el.dataset.id, agizo } }));
  },
  "pakia": async (el) => {
    const f = await chaguaFaili("image/*");
    if (!f) return;
    const form = new FormData();
    form.append("lengo", el.dataset.lengo); form.append("id", el.dataset.id); form.append("geuza", el.dataset.geuza); form.append("faili", f);
    try {
      const r = await api("/api/hs/pakia", { form });
      if (r.id) fuatilia(r); else { await pakia(); toast("📷 Picha imewekwa", "ok"); }
    } catch (e) { kosa(e); }
  },
  "rudisha": async (el) => {
    try { await api("/api/hs/rudisha", { body: { lengo: el.dataset.lengo, id: el.dataset.id } }); await pakia(); toast("↩️ Toleo la awali limerudishwa", "ok"); } catch (e) { kosa(e); }
  },

  // video
  "vo": () => { S.vo.kichwa = $("#vo-kichwa").checked; S.vo.manukuu = $("#vo-manukuu").checked; },
  "mp-kina": async (el) => { await api("/api/hs/hadithi/msingi", { body: { mipangilio: { kina_2_5d: el.checked } } }); },
  "video": () => anzisha(api("/api/hs/kazi/video", { body: { kichwa: S.vo.kichwa, manukuu: S.vo.manukuu } })),
  "muziki": async () => {
    const f = await chaguaFaili("audio/*");
    if (!f) return;
    const form = new FormData(); form.append("faili", f);
    try { await api("/api/hs/muziki", { form }); await pakia(); toast("🎵 Muziki umewekwa", "ok"); } catch (e) { kosa(e); }
  },
  "muziki-ondoa": async () => { await api("/api/hs/muziki/ondoa", { body: {} }); await pakia(); },

  // mipangilio
  "key": async () => {
    try { await api("/api/hs/key", { body: { api_key: $("#key").value } }); await pakia(); toast("🔑 Key imehifadhiwa kwa kipindi hiki", "ok"); } catch (e) { kosa(e); }
  },
  "mtindo": (el) => { $("#s-mtindo").value = el.dataset.v; ACT["chagua-opt"](el); },
  "hifadhi-msingi": async () => {
    try { await api("/api/hs/hadithi/msingi", { body: { kichwa: $("#s-kichwa").value, mtindo: $("#s-mtindo").value, ukubwa: thamani("#s-ukubwa") } }); await pakia(); toast("💾 Imehifadhiwa", "ok"); } catch (e) { kosa(e); }
  },
  "hifadhi-ubora": async () => {
    try {
      await api("/api/hs/hadithi/msingi", { body: { mipangilio: { nguvu_ya_mhusika: +$("#s-nguvu").value, onyesha_jina: $("#s-jina").checked, mbegu: +$("#s-mbegu").value } } });
      await pakia(); toast("💾 Imehifadhiwa", "ok");
    } catch (e) { kosa(e); }
  },
  "hifadhi-yaml": async () => { try { await api("/api/hs/hadithi/yaml", { body: { yaml: $("#s-yaml").value } }); await pakia(); toast("💾 YAML imetumika", "ok"); } catch (e) { kosa(e); } },
};

/* ------------------------------------------------------------------ matukio ya ukurasa */
document.addEventListener("click", (e) => {
  const go = e.target.closest("[data-go]");
  if (go) { e.preventDefault(); funga(); enda(go.dataset.go); return; }
  const el = e.target.closest("[data-act]");
  if (el && ACT[el.dataset.act] && !(el.tagName === "INPUT" && el.type === "range")) {
    if (el.tagName === "A") e.preventDefault();
    ACT[el.dataset.act](el, e);
  }
});
document.addEventListener("change", async (e) => {
  if (e.target.id === "vo-nguvu") {
    try { await api("/api/hs/hadithi/msingi", { body: { mipangilio: { nguvu_ya_mwendo: +e.target.value } } }); } catch (er) { kosa(er); }
  }
});
document.addEventListener("keydown", (e) => {
  if (e.target.id === "ujumbe" && e.key === "Enter" && !e.shiftKey) { e.preventDefault(); tuma(); }
  if (e.target.id === "agizo" && e.key === "Enter") { e.preventDefault(); $('[data-act="hariri"]')?.click(); }
  if (e.key === "Escape") funga();
});
document.addEventListener("input", (e) => {
  if (e.target.id === "ujumbe") { e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 180) + "px"; }
});

/* mandhari: giza / mwanga */
(() => {
  const t = localStorage.getItem("hs-theme");
  if (t) document.documentElement.dataset.theme = t;
  $("#mandhari").onclick = () => {
    const sasa = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    const mpya = sasa === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = mpya;
    localStorage.setItem("hs-theme", mpya);
  };
})();

pakia().catch((e) => { $("#main").innerHTML = `<div class="empty"><div class="big">⚠️</div>Imeshindikana kupakia Studio: ${esc(e.message)}<br><br><button class="btn" onclick="location.reload()">Jaribu tena</button></div>`; });
