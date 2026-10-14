/* COREBURN overlay: shared chat (Twitch + Kick, copied from overlay.html) + goal + socials. */
const DEFAULTS = { channel:"calebgcameron", kick:"calebgcameron", kick_chatroom:"",
  kick_ws:"wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=8.4.0&flash=false",
  platbadge:1, badges:1, emotes:1, hidebots:1, hidecmds:1, fade:0, max:9, goal:1, goalfile:"goal.json", goalpoll:30 };
const qs = new URLSearchParams(location.search);
const P = (k) => qs.has(k) ? qs.get(k) : DEFAULTS[k];
const N = (k, d) => { const v = parseFloat(P(k)); return Number.isFinite(v) ? v : d; };
const B = (k) => { const v = String(P(k)); return v === "1" || v === "true" || v === "yes"; };
const layoutName = "game";
const DEMO = B("demo"), DEBUG = B("debug");
const $ = (id) => document.getElementById(id);
const dbg = (s) => { if (DEBUG) console.log("[overlay]", s); };
window.__overlay = { status: "init", joined: false, messages: 0, byPlat: {}, errors: [] };
const MAX = Math.max(1, Math.round(N("max", 9)));
const FADE = (() => { const f = N("fade", 0); return f <= 0 ? 0 : (f < 5 ? 30 : f); })();
const BOTS = new Set(["nightbot","streamelements","streamlabs","moobot","fossabot","wizebot","soundalerts","sery_bot","botrixoficial","kofistreambot","kickbot"]);
const PLAT_ICON = {
  tw: '<svg viewBox="0 0 24 24"><path d="M2.15 0 .54 4.12v16.84h5.73V24h3.22l3.05-3.04h4.66L23.46 14.69V0zm19.16 13.61-3.58 3.58H12l-3.05 3.05v-3.05H4.12V2.15h17.19zM17.73 6.27v6.26h-2.15V6.27zm-5.73 0v6.26H9.85V6.27z"/></svg>',
  kick: '<svg viewBox="0 0 24 24"><path d="M2 2h7v6h2V6h2V4h2V2h7v7h-2v2h-2v2h2v2h2v7h-7v-2h-2v-2h-2v-2H9v6H2z"/></svg>'
};
const PALETTE = ["#ff4a4a","#4aa3ff","#3fd47f","#b86bff","#ff8c3a","#2ed1d1","#ff5fb2","#e8d44d","#8fa6ff","#7ee06a"];
let chatEl = null;

function safeColor(c, name) {
  let col = /^#[0-9a-f]{6}$/i.test(c || "") ? c : null;
  if (!col) { let h = 0; for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0; col = PALETTE[h % PALETTE.length]; }
  // lift very dark colours so they're readable on the dark backing
  let r = parseInt(col.slice(1,3),16), g = parseInt(col.slice(3,5),16), b = parseInt(col.slice(5,7),16);
  const lum = 0.2126*r + 0.7152*g + 0.0722*b;
  if (lum < 110) { const k = (110 - lum) / 255 + 0.35; r = Math.round(r + (255-r)*k); g = Math.round(g + (255-g)*k); b = Math.round(b + (255-b)*k); }
  return `rgb(${r},${g},${b})`;
}

function parseTags(s) {
  const t = {};
  if (!s) return t;
  for (const kv of s.split(";")) {
    const i = kv.indexOf("="); const k = i < 0 ? kv : kv.slice(0, i); let v = i < 0 ? "" : kv.slice(i + 1);
    v = v.replace(/\\s/g, " ").replace(/\\:/g, ";").replace(/\\r/g, "").replace(/\\n/g, "").replace(/\\\\/g, "\\");
    t[k] = v;
  }
  return t;
}
function parseLine(line) {
  // [@tags] [:prefix] COMMAND [params] [:trailing]
  let p = 0, tags = {}, prefix = "", cmd = "", params = [], trailing = null;
  if (line[0] === "@") { const e = line.indexOf(" "); tags = parseTags(line.slice(1, e)); p = e + 1; }
  if (line[p] === ":") { const e = line.indexOf(" ", p); prefix = line.slice(p + 1, e); p = e + 1; }
  const ti = line.indexOf(" :", p - 1);
  let mid = ti >= 0 ? line.slice(p, ti) : line.slice(p);
  if (ti >= 0) trailing = line.slice(ti + 2);
  const parts = mid.trim().split(" "); cmd = parts.shift(); params = parts;
  return { tags, prefix, cmd, params, trailing, nick: prefix.split("!")[0] };
}

// Build message text as DOM nodes (never innerHTML) with Twitch emote images from the "emotes" tag.
function buildText(container, text, emotesTag) {
  const chars = Array.from(text);               // Twitch emote ranges index by code point
  const ranges = [];
  if (B("emotes") && emotesTag) {
    for (const part of emotesTag.split("/")) {
      const [id, locs] = part.split(":");
      if (!id || !locs || !/^[A-Za-z0-9_]+$/.test(id)) continue;
      for (const loc of locs.split(",")) {
        const [a, b] = loc.split("-").map(Number);
        if (Number.isInteger(a) && Number.isInteger(b) && a <= b && b < chars.length) ranges.push({ a, b, id });
      }
    }
    ranges.sort((m, n) => m.a - n.a);
  }
  let i = 0;
  for (const r of ranges) {
    if (r.a < i) continue;
    if (r.a > i) container.appendChild(document.createTextNode(chars.slice(i, r.a).join("")));
    const img = document.createElement("img");
    img.className = "emote"; img.alt = chars.slice(r.a, r.b + 1).join("");
    img.src = `https://static-cdn.jtvnw.net/emoticons/v2/${r.id}/default/dark/1.0`;
    img.onerror = () => img.replaceWith(document.createTextNode(img.alt));
    container.appendChild(img);
    i = r.b + 1;
  }
  if (i < chars.length) container.appendChild(document.createTextNode(chars.slice(i).join("")));
}

// Trim from the top: over MAX, or no longer fully inside the box (it stacks from the bottom, newest last).
// Trimmed messages fade out over .3s instead of vanishing; nothing below them moves when they go.
function leave(el) { if (el.classList.contains("leaving")) return; el.classList.add("leaving"); setTimeout(() => el.remove(), 320); }
function fitChat() {
  if (!chatEl) return;
  const live = Array.from(chatEl.children).filter(c => !c.classList.contains("leaving"));
  let extra = live.length - MAX;
  for (let i = 0; i < live.length - 1; i++) {
    if (extra > 0 || live[i].offsetTop < 0) { leave(live[i]); extra--; } else break;
  }
}
// Smooth scroll: messages already on screen glide up (FLIP) when a new one lands at the bottom.
function glide(before) {
  for (const [c, top] of before) {
    if (!c.isConnected) continue;
    const d = top - c.getBoundingClientRect().top;
    if (Math.abs(d) > 0.5 && c.animate) c.animate([{ transform: `translateY(${d}px)` }, { transform: "none" }], { duration: 280, easing: "cubic-bezier(.2,.7,.3,1)" });
  }
}
function addMessage({ name, color, text, emotes, badges, id, userId, system, plat, build }) {
  if (!chatEl) return;
  plat = plat || "tw";
  const el = document.createElement("div");
  el.className = "msg";
  el.dataset.plat = plat;
  if (id) el.dataset.id = plat + ":" + id;
  if (userId) el.dataset.user = plat + ":" + userId;
  if (B("platbadge")) { const pb = document.createElement("span"); pb.className = "plat p-" + plat; pb.innerHTML = PLAT_ICON[plat] || ""; el.appendChild(pb); }
  const b = badges || "";
  if (/broadcaster\//.test(b)) el.classList.add("bc"); else if (/moderator\//.test(b)) el.classList.add("mod"); else if (/vip\//.test(b)) el.classList.add("vip");
  if (system) {
    el.classList.add("system");
    const s = document.createElement("span"); s.className = "sys"; s.textContent = system; el.appendChild(s);
    if (text) { el.appendChild(document.createElement("br")); }
  }
  if (name && text) {
    if (B("badges")) {
      const add = (cls, label) => { const s = document.createElement("span"); s.className = "badge " + cls; s.textContent = label; el.appendChild(s); };
      if (/broadcaster\//.test(b)) add("b-bc", "LIVE");
      else if (/moderator\//.test(b)) add("b-mod", "MOD");
      else if (/vip\//.test(b)) add("b-vip", "VIP");
      if (/(^|,)(subscriber|founder)\//.test(b)) add("b-sub", "SUB");
    }
    let action = false;
    const m = /^\u0001ACTION (.*)\u0001$/.exec(text); if (m) { text = m[1]; action = true; }
    const n = document.createElement("span"); n.className = "name"; n.textContent = name; n.style.color = safeColor(color, name); el.appendChild(n);
    if (!action) { const c = document.createElement("span"); c.className = "colon"; c.textContent = ":"; el.appendChild(c); }
    const t = document.createElement("span"); t.className = "text" + (action ? " action" : ""); if (action) t.style.color = safeColor(color, name);
    (build || buildText)(t, text, emotes); el.appendChild(t);
  } else if (text) {
    const t = document.createElement("span"); t.className = "text"; (build || buildText)(t, text, emotes); el.appendChild(t);
  }
  const before = new Map(); for (const c of chatEl.children) before.set(c, c.getBoundingClientRect().top);
  chatEl.appendChild(el);
  window.__overlay.messages++;
  window.__overlay.byPlat[plat] = (window.__overlay.byPlat[plat] || 0) + 1;
  fitChat(); glide(before);
  requestAnimationFrame(fitChat); setTimeout(fitChat, 400); // after emotes/fonts settle
  if (FADE > 0) setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 1000); }, FADE * 1000);
}
function removeMsgs(sel) { if (chatEl) chatEl.querySelectorAll(sel).forEach(leave); }

function startTwitch(channel) {
  channel = String(channel || "").toLowerCase().replace(/^#/, "").replace(/[^a-z0-9_]/g, "");
  if (!channel) { window.__overlay.status = "no-channel"; dbg("no channel"); return; }
  let ws, backoff = 1000, pingTimer = null, lastData = Date.now();
  const connect = () => {
    window.__overlay.status = "connecting"; dbg("connecting #" + channel);
    ws = new WebSocket("wss://irc-ws.chat.twitch.tv:443");
    ws.onopen = () => {
      ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands");
      ws.send("PASS SCHMOOPIIE");
      ws.send("NICK justinfan" + (10000 + Math.floor(Math.random() * 89999)));
      ws.send("JOIN #" + channel);
      window.__overlay.status = "open";
    };
    ws.onmessage = (ev) => {
      lastData = Date.now();
      for (const line of String(ev.data).split("\r\n")) {
        if (!line) continue;
        if (line.startsWith("PING")) { ws.send("PONG" + line.slice(4)); continue; }
        const m = parseLine(line);
        switch (m.cmd) {
          case "001": backoff = 1000; break;
          case "366": case "ROOMSTATE":
            if (!window.__overlay.joined) { window.__overlay.joined = true; window.__overlay.status = "joined"; dbg("joined #" + channel); }
            break;
          case "PRIVMSG": {
            const name = m.tags["display-name"] || m.nick;
            const login = (m.nick || "").toLowerCase();
            const text = m.trailing || "";
            if (B("hidebots") && BOTS.has(login)) break;
            if (B("hidecmds") && text.startsWith("!")) break;
            addMessage({ name, color: m.tags.color, text, emotes: m.tags.emotes, badges: m.tags.badges, id: m.tags.id, userId: m.tags["user-id"] });
            break;
          }
          case "USERNOTICE": {
            const sys = m.tags["system-msg"] || "";
            if (sys) addMessage({ system: sys, name: m.tags["display-name"], color: m.tags.color, text: m.trailing || "", emotes: m.tags.emotes, badges: m.tags.badges, id: m.tags.id });
            break;
          }
          case "CLEARCHAT": // ban/timeout (or full clear)
            if (!chatEl) break;
            if (m.tags["target-user-id"]) removeMsgs(`.msg[data-user="${CSS.escape("tw:" + m.tags["target-user-id"])}"]`);
            else removeMsgs('.msg[data-plat="tw"]');
            break;
          case "CLEARMSG":
            if (chatEl && m.tags["target-msg-id"]) removeMsgs(`.msg[data-id="${CSS.escape("tw:" + m.tags["target-msg-id"])}"]`);
            break;
          case "RECONNECT": try { ws.close(); } catch (e) {} break;
          case "NOTICE": window.__overlay.errors.push(m.trailing); dbg("NOTICE: " + m.trailing); break;
        }
      }
    };
    ws.onclose = () => {
      window.__overlay.joined = false; window.__overlay.status = "reconnecting";
      dbg("disconnected, retry in " + backoff / 1000 + "s");
      setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 30000);
    };
    ws.onerror = () => { window.__overlay.errors.push("ws error"); };
  };
  connect();
  // watchdog: Twitch PINGs ~every 5 min; if nothing for 7 min, force reconnect
  pingTimer = setInterval(() => { if (Date.now() - lastData > 420000 && ws) { try { ws.close(); } catch (e) {} } }, 30000);
}

/* ---------------- KICK (read-only, no login) ----------------
   Kick chat runs on Pusher. Public channel "chatrooms.<chatroomId>.v2", events App\Events\ChatMessageEvent etc.
   chatroomId: ?kick_chatroom= / site-config > built-in KICK_ROOMS > cached lookup > https://kick.com/api/v2/channels/<slug>
   (the lookup is behind Cloudflare and may be blocked for browsers, hence the built-in id). */
const KICK_ROOMS = { calebgcameron: 95824000 };
async function kickRoomId(slug) {
  const forced = parseInt(P("kick_chatroom"), 10);
  if (forced > 0) return forced;
  if (KICK_ROOMS[slug]) return KICK_ROOMS[slug];
  const key = "kickroom:" + slug;
  try { const c = parseInt(localStorage.getItem(key), 10); if (c > 0) return c; } catch (e) {}
  for (const u of [`https://kick.com/api/v2/channels/${slug}/chatroom`, `https://kick.com/api/v2/channels/${slug}`]) {
    try {
      const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 6000);
      const r = await fetch(u, { headers: { Accept: "application/json" }, signal: ctl.signal }); clearTimeout(to);
      if (!r.ok) continue;
      const d = await r.json(); const id = (d && d.chatroom && d.chatroom.id) || (d && d.chatable_id === undefined && d.id);
      if (id > 0) { try { localStorage.setItem(key, String(id)); } catch (e) {} return id; }
    } catch (e) { dbg("kick lookup failed: " + (e && e.message)); }
  }
  return 0;
}
// "[emote:37226:KEKW] hi" -> <img> + text (DOM nodes only)
function kickText(container, text) {
  const re = /\[emote:(\d+):([^\]]*)\]/g; let i = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > i) container.appendChild(document.createTextNode(text.slice(i, m.index)));
    if (B("emotes")) {
      const img = document.createElement("img"); img.className = "emote"; img.alt = m[2];
      img.src = `https://files.kick.com/emotes/${m[1]}/fullsize`;
      img.onerror = () => img.replaceWith(document.createTextNode(img.alt));
      container.appendChild(img);
    } else container.appendChild(document.createTextNode(m[2]));
    i = re.lastIndex;
  }
  if (i < text.length) container.appendChild(document.createTextNode(text.slice(i)));
}
const KICK_BADGE = { broadcaster: "broadcaster", moderator: "moderator", vip: "vip", subscriber: "subscriber", founder: "founder", og: "og", staff: "staff", verified: "verified" };
function startKick(slugRaw) {
  const slug = String(slugRaw || "").toLowerCase().trim().replace(/[^a-z0-9_-]/g, "");
  const K = window.__overlay.kick = { status: "init", slug, room: 0, messages: 0 };
  if (!slug || ["0", "off", "false", "no"].includes(String(slugRaw).toLowerCase())) { K.status = "off"; return; }
  let ws, backoff = 1000, lastData = Date.now(), room = 0, pinger = null;
  const connect = async () => {
    if (!room) room = K.room = await kickRoomId(slug);
    if (!room) { K.status = "no-chatroom"; dbg("kick: no chatroom id for " + slug + " (set ?kick_chatroom=)"); setTimeout(connect, Math.min(backoff *= 2, 60000)); return; }
    K.status = "connecting"; dbg("kick connecting " + slug + " #" + room);
    try { ws = new WebSocket(P("kick_ws")); } catch (e) { K.status = "bad-ws"; return; }
    ws.onmessage = (ev) => {
      lastData = Date.now();
      let j; try { j = JSON.parse(ev.data); } catch (e) { return; }
      let d = j.data; if (typeof d === "string") { try { d = JSON.parse(d); } catch (e) {} }
      switch (j.event) {
        case "pusher:connection_established":
          ws.send(JSON.stringify({ event: "pusher:subscribe", data: { auth: "", channel: `chatrooms.${room}.v2` } }));
          break;
        case "pusher_internal:subscription_succeeded": backoff = 1000; K.status = "joined"; dbg("kick joined " + slug); break;
        case "pusher:ping": ws.send(JSON.stringify({ event: "pusher:pong", data: {} })); break;
        case "pusher:error": window.__overlay.errors.push("kick: " + JSON.stringify(d)); dbg("kick error " + JSON.stringify(d)); break;
        case "App\\Events\\ChatMessageEvent": {
          if (!d || !d.sender) break;
          const s = d.sender, idn = s.identity || {}, text = String(d.content || "");
          const login = String(s.slug || s.username || "").toLowerCase();
          if (B("hidebots") && BOTS.has(login)) break;
          if (B("hidecmds") && text.startsWith("!")) break;
          const badges = (idn.badges || []).map(b => KICK_BADGE[b && b.type]).filter(Boolean).map(t => t + "/1").join(",");
          K.messages++;
          addMessage({ plat: "kick", name: s.username || s.slug, color: idn.color, text, badges, id: d.id, userId: s.id, build: kickText });
          break;
        }
        case "App\\Events\\MessageDeletedEvent":
          if (d && d.message && d.message.id) removeMsgs(`.msg[data-id="${CSS.escape("kick:" + d.message.id)}"]`);
          break;
        case "App\\Events\\UserBannedEvent":
          if (d && d.user && d.user.id) removeMsgs(`.msg[data-user="${CSS.escape("kick:" + d.user.id)}"]`);
          break;
        case "App\\Events\\ChatroomClearEvent": removeMsgs('.msg[data-plat="kick"]'); break;
      }
    };
    ws.onclose = (e) => {
      K.status = "reconnecting"; dbg("kick disconnected (" + (e && e.code) + "), retry in " + backoff / 1000 + "s");
      setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 30000);
    };
    ws.onerror = () => { window.__overlay.errors.push("kick ws error"); };
  };
  connect();
  // keep-alive (Pusher activity_timeout is 120s) + watchdog: nothing heard for 3 min -> reconnect
  pinger = setInterval(() => {
    if (!ws || ws.readyState !== 1) return;
    if (Date.now() - lastData > 180000) { try { ws.close(); } catch (e) {} return; }
    try { ws.send(JSON.stringify({ event: "pusher:ping", data: {} })); } catch (e) {}
  }, 60000);
}


/* ---------- goal (goal.json) ---------- */
function renderGoal(d) {
  const g = $("goal"); if (!g) return;
  if (!d || d.show === false || !B("goal")) { g.classList.add("hidden"); return; }
  const raised = +d.raised || 0, goal = Math.max(1, +d.goal || 1), pct = Math.min(100, Math.round(raised / goal * 100));
  g.querySelector(".g-title").textContent = d.title || "GOAL";
  g.querySelector(".g-amt").textContent = "$" + Math.round(raised) + " / $" + Math.round(goal) + " " + (d.currency || "");
  g.querySelector(".g-bar b").style.width = pct + "%";
  g.querySelector(".g-pct").textContent = pct + "%";
  const t = g.querySelector(".g-tip"); t.textContent = d.tip_url ? (d.tip_label || "TIP") + ": " + d.tip_url : ""; t.style.display = d.tip_url ? "" : "none";
  g.classList.remove("hidden");
}
function startGoal() {
  if (DEMO) { renderGoal({ title: "STARLINK GOAL", raised: 385, goal: 1000, currency: "NZD", tip_url: "streamelements.com/calebgcameron/tip" }); return; }
  let last = "";
  const tick = async () => { try { const r = await fetch(P("goalfile") + "?t=" + Date.now(), { cache: "no-store" }); const txt = await r.text();
    if (txt !== last) { last = txt; renderGoal(JSON.parse(txt)); } } catch (e) { window.__overlay.errors.push("goal: " + e.message); } };
  tick(); setInterval(tick, Math.max(10, N("goalpoll", 30)) * 1000);
}
function demoChat() {
  const S = [
    { name: "slagyard_sam", color: "#FF8C3A", text: "the Grindchoir boss music goes hard" },
    { name: "Mod_Example", color: "#00b36b", text: "join the room: sublebow.github.io/coreburn", badges: "moderator/1" },
    { name: "viewer2", color: "#4aa3ff", text: "Iskra ult cleared the whole wave 🔥" },
    { name: "lurker_42", color: "#B86BFF", text: "what's the room code??", badges: "subscriber/3" },
    { plat: "kick", name: "KickViewer", color: "#53FC18", text: "Orin tank build is busted", build: kickText },
    { name: "viewer3", color: "#E8D44D", text: "wave 20 or bust" }
  ];
  S.forEach((m, i) => setTimeout(() => addMessage(m), i * 60));
}
function startOverlay() {
  chatEl = $("chat");
  if (chatEl) { if (DEMO) demoChat(); else { startTwitch(P("channel")); if (P("kick") && P("kick") !== "0") startKick(P("kick")); } }
  startGoal();
}
