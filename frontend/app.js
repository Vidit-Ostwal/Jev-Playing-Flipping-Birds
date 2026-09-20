const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const overlay = document.getElementById("overlay");
const overlayText = overlay.querySelector("p");
const scoreEl = document.getElementById("score");
const actionEl = document.getElementById("action");
const metaEl = document.getElementById("meta");
const badgeEl = document.getElementById("badge");
const noteEl = document.getElementById("note");
const pFlap = document.getElementById("p-flap");
const pNoop = document.getElementById("p-noop");
const pFlapN = document.getElementById("p-flap-n");
const pNoopN = document.getElementById("p-noop-n");
const logsEl = document.getElementById("logs");
const shoutBox = document.getElementById("shout");
const startBtn = document.getElementById("start");
const pauseBtn = document.getElementById("pause");

const proto = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(`${proto}://${location.host}/ws`);
let lastYell = "";
const clips = {};

function selectedAgent() {
  return document.querySelector("input[name=agent]:checked").value;
}

function fallbackOn() {
  return document.getElementById("fallback").checked;
}

function shoutOn() {
  return shoutBox.checked;
}

function send(payload) {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

function setRunning(running) {
  startBtn.disabled = running;
  pauseBtn.disabled = !running;
}

function showOverlay(text) {
  overlayText.textContent = text;
  overlay.classList.remove("hidden");
}

function hideOverlay() {
  overlay.classList.add("hidden");
}

function start() {
  hideOverlay();
  setRunning(true);
  send({
    type: "start",
    agent: selectedAgent(),
    fallback: fallbackOn(),
    shout: shoutOn(),
  });
}

startBtn.addEventListener("click", start);
pauseBtn.addEventListener("click", () => send({ type: "pause" }));
document.getElementById("reset").addEventListener("click", () => {
  setRunning(false);
  showOverlay("Start to fly");
  logsEl.replaceChildren();
  actionEl.textContent = "ready";
  actionEl.style.fontSize = "";
  actionEl.classList.remove("is-flap", "is-noop");
  lastYell = "";
  metaEl.textContent = "Waiting for the first call.";
  send({ type: "reset" });
});

document.querySelectorAll("input[name=agent]").forEach((input) => {
  input.addEventListener("change", () => {
    send({ type: "set_agent", agent: selectedAgent(), fallback: fallbackOn() });
  });
});
document.getElementById("fallback").addEventListener("change", () => {
  send({ type: "set_agent", agent: selectedAgent(), fallback: fallbackOn() });
});
shoutBox.addEventListener("change", () => {
  send({ type: "set_voice", shout: shoutOn() });
});

function pct(value) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function drawFrame(dataUrl) {
  const image = new Image();
  image.onload = () => ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  image.src = dataUrl;
}

function sizeForConfidence(confidence) {
  const sure = confidence == null ? 0.45 : Math.min(1, Math.max(0, Number(confidence)));
  return `${1.8 + sure * 3.6}rem`;
}

function slam(word, confidence) {
  actionEl.textContent = word;
  actionEl.style.fontSize = sizeForConfidence(confidence);
  actionEl.classList.toggle("is-flap", word === "flap");
  actionEl.classList.toggle("is-noop", word === "noop");
  if (word === lastYell) return;
  lastYell = word;
  actionEl.classList.remove("slam");
  void actionEl.offsetWidth;
  actionEl.classList.add("slam");
}

function appendLog(msg) {
  const item = document.createElement("li");
  item.dataset.action = msg.action;
  const conf = msg.confidence == null ? "—" : pct(msg.confidence);
  const latency = msg.latency_ms == null ? "—" : `${msg.latency_ms} ms`;
  item.innerHTML = `<b>${msg.action}</b> ${conf} ${latency}`;
  logsEl.prepend(item);
  while (logsEl.children.length > 24) {
    logsEl.lastElementChild.remove();
  }
}

function loadBank(bank) {
  Object.entries(bank || {}).forEach(([name, audioB64]) => {
    const clip = new Audio(`data:audio/mpeg;base64,${audioB64}`);
    clip.preload = "auto";
    clips[name] = clip;
  });
}

function playShout(name) {
  const clip = clips[name];
  if (!clip || !shoutOn()) return;
  clip.pause();
  clip.currentTime = 0;
  clip.play().catch(() => {});
}

socket.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "voice_bank") {
    loadBank(msg.clips);
    return;
  }
  if (msg.type === "log") {
    appendLog(msg);
    return;
  }
  if (msg.type === "status") {
    setRunning(Boolean(msg.running));
    return;
  }
  if (msg.type !== "frame") return;

  if (msg.image) {
    drawFrame(`data:image/jpeg;base64,${msg.image}`);
  }
  scoreEl.textContent = String(msg.score ?? 0);
  if (msg.action) {
    slam(msg.action, msg.confidence);
    playShout(msg.action);
  }

  const latency = msg.latency_ms == null ? "—" : `${Math.round(msg.latency_ms)} ms`;
  const conf = msg.confidence == null ? "—" : pct(msg.confidence);
  metaEl.textContent = `${msg.source || "jev"}  ${conf}  ${latency}  step ${msg.steps ?? 0}`;

  const flap = msg.probabilities?.flap;
  const noop = msg.probabilities?.noop;
  pFlap.style.width = flap == null ? "0%" : `${flap * 100}%`;
  pNoop.style.width = noop == null ? "0%" : `${noop * 100}%`;
  pFlapN.textContent = pct(flap);
  pNoopN.textContent = pct(noop);

  badgeEl.classList.toggle("hidden", !msg.fallback);
  noteEl.textContent = msg.error || "";

  if (msg.terminated) {
    setRunning(false);
    showOverlay("Bird down. Reset to fly again.");
  }
});

socket.addEventListener("open", () => {
  showOverlay("Start to fly");
  startBtn.disabled = false;
});

socket.addEventListener("close", () => {
  setRunning(false);
  startBtn.disabled = true;
  showOverlay("Lost the game server. Refresh the page.");
});
