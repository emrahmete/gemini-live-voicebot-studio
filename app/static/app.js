/**
 * Google ADK × Gemini Live Voicebot Studio - Frontend Client
 * Handles:
 *  - 16kHz 16-bit PCM Microphone streaming
 *  - 24kHz 16-bit PCM Gapless Audio Playback + Instant Barge-In (Interruption)
 *  - 1 FPS Camera & Screen Share streaming (Multimodal Live API)
 *  - 6 Industry Use-Case Scenarios & 3 Gemini Live Architecture Modes
 *  - Dynamic ADK Tool Widget Canvas & Gemini 3.8 Flash Executive Call Summary
 */

const state = {
  config: null,
  selectedScenarioId: "banking_vip",
  selectedModeId: "native_audio",
  selectedVoice: "Kore",
  ws: null,
  connected: false,
  micActive: false,
  cameraActive: false,
  screenActive: false,
  audioCtx: null,
  micStream: null,
  micProcessor: null,
  mediaStream: null,
  frameTimer: null,
  nextPlayTime: 0,
  activeAudioSources: [],
  activeUserBubble: null,
  activeModelBubble: null,
  transcriptHistory: [],
  micLevel: 0,
  speakerLevel: 0,
  orbStatus: "OTURUMU BAŞLATIN VEYA DEMO KOMUTU SEÇİN",
};

// DOM Elements
const el = {
  archModeList: document.getElementById("archModeList"),
  voiceSelect: document.getElementById("voiceSelect"),
  scenarioList: document.getElementById("scenarioList"),
  heroIcon: document.getElementById("heroIcon"),
  heroTitle: document.getElementById("heroTitle"),
  heroSubtitle: document.getElementById("heroSubtitle"),
  heroHighlights: document.getElementById("heroHighlights"),
  activeModelPills: document.getElementById("activeModelPills"),
  activeArchBadge: document.getElementById("activeArchBadge"),
  connStatusDot: document.getElementById("connStatusDot"),
  connStatusText: document.getElementById("connStatusText"),
  orbStateBadge: document.getElementById("orbStateBadge"),
  audioCanvas: document.getElementById("audioCanvas"),
  videoPreviewBox: document.getElementById("videoPreviewBox"),
  liveVideo: document.getElementById("liveVideo"),
  frameCaptureCanvas: document.getElementById("frameCaptureCanvas"),
  btnConnect: document.getElementById("btnConnect"),
  btnConnectLabel: document.getElementById("btnConnectLabel"),
  btnMic: document.getElementById("btnMic"),
  btnMicLabel: document.getElementById("btnMicLabel"),
  btnCamera: document.getElementById("btnCamera"),
  btnScreen: document.getElementById("btnScreen"),
  btnInterrupt: document.getElementById("btnInterrupt"),
  sampleChipsContainer: document.getElementById("sampleChipsContainer"),
  chatFeed: document.getElementById("chatFeed"),
  textForm: document.getElementById("textForm"),
  textInput: document.getElementById("textInput"),
  widgetsCanvas: document.getElementById("widgetsCanvas"),
  telemetryLog: document.getElementById("telemetryLog"),
  btnExecSummary: document.getElementById("btnExecSummary"),
  btnClearLogs: document.getElementById("btnClearLogs"),
};

// ============================================================================
// 1. INITIALIZATION & CONFIG LOADING
// ============================================================================
async function initStudio() {
  // Browsers disable navigator.mediaDevices (Camera/Mic/Screen) on http://0.0.0.0
  // Redirect automatically to http://localhost so WebRTC Secure Context is active.
  if (window.location.hostname === "0.0.0.0") {
    const targetUrl = `http://localhost:${window.location.port || 8090}${window.location.pathname}${window.location.search}`;
    window.location.replace(targetUrl);
    return;
  }

  try {
    const res = await fetch("/api/config");
    state.config = await res.json();
    const projBadge = document.getElementById("gcpProjectBadge");
    if (projBadge) {
      projBadge.textContent = "Gemini Enterprise";
    }
    renderArchitectureModes();
    renderVoices();
    renderScenarios();
    updateScenarioHero();
    startVisualizerAnimation();
    logTelemetry("Studio hazır. Platform: Gemini Enterprise", "success");
  } catch (err) {
    logTelemetry("Yapılandırma yüklenemedi: " + err.message, "interrupt");
  }
}

function renderArchitectureModes() {
  const modes = state.config.architecture_modes;
  el.archModeList.innerHTML = "";
  Object.values(modes).forEach((m) => {
    const div = document.createElement("div");
    div.className = `arch-card ${m.id === state.selectedModeId ? "active" : ""}`;
    div.innerHTML = `
      <div class="arch-card-top">
        <span class="arch-card-title">${m.short_name}</span>
        <span class="arch-card-badge">${m.badge}</span>
      </div>
      <div class="arch-card-desc">${m.description}</div>
    `;
    div.addEventListener("click", () => selectArchitectureMode(m.id));
    el.archModeList.appendChild(div);
  });
}

function renderVoices() {
  el.voiceSelect.innerHTML = "";
  state.config.voices.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = v.label;
    if (v.id === state.selectedVoice) opt.selected = true;
    el.voiceSelect.appendChild(opt);
  });
  el.voiceSelect.addEventListener("change", (e) => {
    state.selectedVoice = e.target.value;
    if (state.connected) reconnectSession();
  });
}

function renderScenarios() {
  const scenarios = state.config.scenarios;
  el.scenarioList.innerHTML = "";
  Object.values(scenarios).forEach((sc) => {
    const div = document.createElement("div");
    div.className = `scenario-card ${sc.id === state.selectedScenarioId ? "active" : ""}`;
    div.innerHTML = `
      <div class="sc-icon">${sc.icon}</div>
      <div>
        <div class="sc-title">${sc.name.replace(/^[^\s]+\s/, "")}</div>
        <div class="sc-sub">${sc.subtitle}</div>
      </div>
    `;
    div.addEventListener("click", () => selectScenario(sc.id));
    el.scenarioList.appendChild(div);
  });
}

function selectArchitectureMode(modeId) {
  state.selectedModeId = modeId;
  renderArchitectureModes();
  updateScenarioHero();
  if (state.connected) reconnectSession();
}

function selectScenario(scenarioId) {
  state.selectedScenarioId = scenarioId;
  const sc = state.config.scenarios[scenarioId];
  if (sc.default_voice) {
    state.selectedVoice = sc.default_voice;
    el.voiceSelect.value = sc.default_voice;
  }
  if (sc.recommended_mode) {
    state.selectedModeId = sc.recommended_mode;
    renderArchitectureModes();
  }
  renderScenarios();
  updateScenarioHero();
  if (state.connected) reconnectSession();
}

function updateScenarioHero() {
  const sc = state.config.scenarios[state.selectedScenarioId];
  const arch = state.config.architecture_modes[state.selectedModeId];

  el.heroIcon.textContent = sc.icon;
  el.heroTitle.textContent = sc.name.replace(/^[^\s]+\s/, "");
  el.heroSubtitle.textContent = sc.subtitle;
  el.activeArchBadge.textContent = arch.short_name;

  el.activeModelPills.innerHTML = `
    <span class="model-chip primary">${arch.primary_model}</span>
    <span class="model-chip secondary">${arch.secondary_model}</span>
  `;

  el.heroHighlights.innerHTML = sc.highlights
    .map((h) => `<span class="hl-item">✦ ${h}</span>`)
    .join("");

  el.sampleChipsContainer.innerHTML = "";
  sc.sample_prompts.forEach((promptText) => {
    const btn = document.createElement("button");
    btn.className = "sample-chip";
    btn.textContent = "▶ " + promptText;
    btn.addEventListener("click", () => sendSamplePrompt(promptText));
    el.sampleChipsContainer.appendChild(btn);
  });
}

// ============================================================================
// 2. WEBSOCKET & ADK LIVE SESSION MANAGEMENT
// ============================================================================
async function connectSession() {
  if (state.connected) {
    disconnectSession();
    return;
  }

  ensureAudioContext();
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${window.location.host}/ws/live?scenario_id=${encodeURIComponent(
    state.selectedScenarioId
  )}&mode=${encodeURIComponent(state.selectedModeId)}&voice=${encodeURIComponent(state.selectedVoice)}`;

  setConnectionUI("connecting");
  const ws = new WebSocket(url);
  state.ws = ws;

  ws.onopen = () => {
    state.connected = true;
    setConnectionUI("connected");
    setOrbStatus("CANLI OTURUM AKTİF — MİKROFONU AÇIN VEYA KOMUT SEÇİN");
    logTelemetry(
      `ADK Live oturumu başlatıldı (${state.selectedModeId} | ${state.selectedScenarioId} | Ses: ${state.selectedVoice})`,
      "success"
    );
  };

  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    handleServerEvent(msg);
  };

  ws.onclose = () => {
    state.connected = false;
    stopMicrophone();
    stopMediaSharing();
    setConnectionUI("disconnected");
    setOrbStatus("OTURUM SONLANDI");
  };

  ws.onerror = () => {
    logTelemetry("WebSocket bağlantı hatası oluştu.", "interrupt");
  };
}

function disconnectSession() {
  stopAllAudioPlayback();
  stopMicrophone();
  stopMediaSharing();
  if (state.ws) {
    state.ws.close();
    state.ws = null;
  }
  state.connected = false;
  setConnectionUI("disconnected");
}

function reconnectSession() {
  disconnectSession();
  setTimeout(() => connectSession(), 250);
}

function setConnectionUI(status) {
  if (status === "connected") {
    el.connStatusDot.className = "status-dot connected";
    el.connStatusText.textContent = "Canlı Bağlı (ADK Bidi Streaming)";
    el.btnConnect.classList.add("connected");
    el.btnConnectLabel.textContent = "Oturumu Kapat";
    el.btnMic.disabled = false;
    el.btnCamera.disabled = false;
    el.btnScreen.disabled = false;
    el.btnInterrupt.disabled = false;
  } else if (status === "connecting") {
    el.connStatusText.textContent = "Gemini Enterprise'a Bağlanılıyor...";
  } else {
    el.connStatusDot.className = "status-dot disconnected";
    el.connStatusText.textContent = "Hazır (Bağlantı Bekleniyor)";
    el.btnConnect.classList.remove("connected");
    el.btnConnectLabel.textContent = "Canlı Oturumu Başlat";
    el.btnMic.disabled = true;
    el.btnCamera.disabled = true;
    el.btnScreen.disabled = true;
    el.btnInterrupt.disabled = true;
  }
}

// ============================================================================
// 3. SERVER EVENT PROCESSING (AUDIO, TRANSCRIPTS, BARGE-IN, ADK TOOLS)
// ============================================================================
function handleServerEvent(msg) {
  switch (msg.type) {
    case "session_ready":
      break;

    case "interrupted":
      stopAllAudioPlayback();
      if (state.activeModelBubble) {
        const meta = state.activeModelBubble.querySelector(".msg-meta");
        if (meta && !meta.innerHTML.includes("BARGE-IN")) {
          meta.innerHTML += ` <span class="interrupted-tag">⚡ SÖZ KESİLDİ (BARGE-IN)</span>`;
        }
        state.activeModelBubble = null;
      }
      setOrbStatus("⚡ SÖZ KESİLDİ (BARGE-IN) — SİZİ DİNLİYOR");
      logTelemetry("Barge-In (Interruption): Model sesi anında durduruldu ve tampon temizlendi.", "interrupt");
      break;

    case "input_transcription":
      appendTranscription("user", msg.text, msg.finished, msg.model || "Canlı ASR");
      setOrbStatus("🎙️ KULLANICI KONUŞUYOR (" + (msg.model || "ASR") + ")");
      break;

    case "output_transcription":
      appendTranscription("model", msg.text, msg.finished, msg.model || "Gemini Live");
      setOrbStatus("🔊 GEMINI YANITLIYOR (" + (msg.model || "Live") + ")");
      break;

    case "audio":
      playPcm24kChunk(msg.data);
      break;

    case "tool_call":
      setOrbStatus(`⚙️ ADK TOOL ÇALIŞIYOR: ${msg.name}()`);
      logTelemetry(
        `🔧 ADK Tool Çağrısı [${msg.model || "ADK"}]: ${msg.name}(${JSON.stringify(msg.args)})`,
        "tool"
      );
      break;

    case "tool_result":
      logTelemetry(`✅ ADK Tool Tamamlandı: ${msg.name}`, "success");
      break;

    case "ui_widget":
      renderWidgetCard(msg.widget);
      break;

    case "turn_complete":
      state.activeUserBubble = null;
      state.activeModelBubble = null;
      setOrbStatus(state.micActive ? "🎙️ DİNLİYOR (CANLI MİKROFON)" : "HAZIR — KONUŞUN VEYA YAZIN");
      break;

    case "error":
      logTelemetry("⚠️ " + msg.message, "interrupt");
      break;
  }
}

function appendTranscription(role, textChunk, isFinished, modelTag) {
  if (!textChunk) return;
  const emptyHint = el.chatFeed.querySelector(".empty-chat-hint");
  if (emptyHint) emptyHint.remove();

  let bubble = role === "user" ? state.activeUserBubble : state.activeModelBubble;
  if (!bubble) {
    bubble = document.createElement("div");
    bubble.className = `msg-bubble ${role}`;
    const roleLabel = role === "user" ? "👤 Müşteri" : "✦ Gemini Asistan";
    bubble.innerHTML = `
      <div class="msg-meta">
        <span>${roleLabel}</span>
        <span>${modelTag}</span>
      </div>
      <div class="msg-text"></div>
    `;
    el.chatFeed.appendChild(bubble);
    if (role === "user") state.activeUserBubble = bubble;
    else state.activeModelBubble = bubble;
  }

  const textNode = bubble.querySelector(".msg-text");
  if (isFinished && textChunk.length >= textNode.textContent.length) {
    textNode.textContent = textChunk;
  } else {
    textNode.textContent += textChunk;
  }

  if (isFinished) {
    state.transcriptHistory.push({ role, text: textNode.textContent });
    if (role === "user") state.activeUserBubble = null;
    else state.activeModelBubble = null;
  }

  el.chatFeed.scrollTop = el.chatFeed.scrollHeight;
}

// ============================================================================
// 4. WEB AUDIO API: 16kHz MIC STREAMING & 24kHz GAPLESS PLAYBACK
// ============================================================================
function ensureAudioContext() {
  if (!state.audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    state.audioCtx = new AudioContextClass({ sampleRate: 24000 });

    // Broadcast-grade Voice Boost chain so AI voice is loud & clear on speaker recordings:
    // Source -> Pre-Gain (2.8x) -> Voice Presence EQ (2.2kHz +4.5dB) -> Soft Limiter/Compressor -> Destination
    const preGain = state.audioCtx.createGain();
    preGain.gain.value = 2.8;

    const presenceFilter = state.audioCtx.createBiquadFilter();
    presenceFilter.type = "peaking";
    presenceFilter.frequency.value = 2200;
    presenceFilter.Q.value = 1.0;
    presenceFilter.gain.value = 4.5;

    const compressor = state.audioCtx.createDynamicsCompressor();
    compressor.threshold.value = -14;
    compressor.knee.value = 12;
    compressor.ratio.value = 4;
    compressor.attack.value = 0.003;
    compressor.release.value = 0.15;

    preGain.connect(presenceFilter);
    presenceFilter.connect(compressor);
    compressor.connect(state.audioCtx.destination);

    state.outputChainInput = preGain;
  }
  if (state.audioCtx.state === "suspended") {
    state.audioCtx.resume();
  }
}

function playPcm24kChunk(base64Data) {
  ensureAudioContext();
  const binaryStr = atob(base64Data);
  const len = binaryStr.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }

  const int16 = new Int16Array(bytes.buffer);
  const float32 = new Float32Array(int16.length);
  let sumSq = 0;
  for (let i = 0; i < int16.length; i++) {
    const sample = int16[i] / 32768.0;
    float32[i] = sample;
    sumSq += sample * sample;
  }
  state.speakerLevel = Math.min(1, Math.sqrt(sumSq / Math.max(1, int16.length)) * 4.5);

  const audioBuffer = state.audioCtx.createBuffer(1, float32.length, 24000);
  audioBuffer.getChannelData(0).set(float32);

  const source = state.audioCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(state.outputChainInput || state.audioCtx.destination);

  const now = state.audioCtx.currentTime;
  if (state.nextPlayTime < now) {
    state.nextPlayTime = now + 0.02;
  }
  source.start(state.nextPlayTime);
  state.nextPlayTime += audioBuffer.duration;
  state.activeAudioSources.push(source);

  source.onended = () => {
    const idx = state.activeAudioSources.indexOf(source);
    if (idx !== -1) state.activeAudioSources.splice(idx, 1);
    if (state.activeAudioSources.length === 0) {
      state.speakerLevel = 0;
    }
  };
}

function stopAllAudioPlayback() {
  state.activeAudioSources.forEach((src) => {
    try {
      src.stop();
    } catch (_) {}
  });
  state.activeAudioSources = [];
  if (state.audioCtx) {
    state.nextPlayTime = state.audioCtx.currentTime;
  }
  state.speakerLevel = 0;
}

function ensureSecureMediaDevices() {
  if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
    return true;
  }
  if (window.location.hostname === "0.0.0.0") {
    const targetUrl = `http://localhost:${window.location.port || 8090}${window.location.pathname}${window.location.search}`;
    window.location.replace(targetUrl);
    return false;
  }
  throw new Error(
    "Tarayıcı kamera/mikrofon erişimi için güvenli bağlam (Secure Context) gerekiyor. Lütfen adresi http://localhost:8090 olarak açın."
  );
}

async function toggleMicrophone() {
  if (state.micActive) {
    stopMicrophone();
    return;
  }
  try {
    if (!ensureSecureMediaDevices()) return;
    ensureAudioContext();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    state.micStream = stream;
    const micCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const source = micCtx.createMediaStreamSource(stream);
    const processor = micCtx.createScriptProcessor(2048, 1, 1);

    processor.onaudioprocess = (e) => {
      if (!state.micActive || !state.connected || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
        return;
      }
      const inputData = e.inputBuffer.getChannelData(0);
      const pcm16 = new Int16Array(inputData.length);
      let sumSq = 0;
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        sumSq += s * s;
      }
      state.micLevel = Math.min(1, Math.sqrt(sumSq / inputData.length) * 6);

      const uint8 = new Uint8Array(pcm16.buffer);
      let binary = "";
      for (let i = 0; i < uint8.byteLength; i++) {
        binary += String.fromCharCode(uint8[i]);
      }
      const b64 = btoa(binary);
      state.ws.send(JSON.stringify({ type: "audio", data: b64 }));
    };

    source.connect(processor);
    processor.connect(micCtx.destination);
    state.micProcessor = { processor, micCtx };
    state.micActive = true;
    el.btnMic.classList.add("active");
    el.btnMicLabel.textContent = "Mikrofon Açık (Dinliyor...)";
    setOrbStatus("🎙️ MİKROFON AKTİF — DOĞRUDAN KONUŞABİLİRSİNİZ");
    logTelemetry("Mikrofon (16kHz PCM) akışı başlatıldı.", "success");
  } catch (err) {
    logTelemetry("Mikrofon erişim hatası: " + err.message, "interrupt");
  }
}

function stopMicrophone() {
  state.micActive = false;
  state.micLevel = 0;
  if (state.micProcessor) {
    try {
      state.micProcessor.processor.disconnect();
      state.micProcessor.micCtx.close();
    } catch (_) {}
    state.micProcessor = null;
  }
  if (state.micStream) {
    state.micStream.getTracks().forEach((t) => t.stop());
    state.micStream = null;
  }
  el.btnMic.classList.remove("active");
  el.btnMicLabel.textContent = "Mikrofonu Aç (Konuş)";
}

// ============================================================================
// 5. MULTIMODAL LIVE VISION: CAMERA & SCREEN SHARE (1 FPS JPEG)
// ============================================================================
async function toggleCameraShare() {
  if (state.cameraActive) {
    stopMediaSharing();
    return;
  }
  stopMediaSharing();
  try {
    if (!ensureSecureMediaDevices()) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    });
    startVideoFrameStreaming(stream, "camera");
  } catch (err) {
    logTelemetry("Kamera açılamadı: " + err.message, "interrupt");
  }
}

async function toggleScreenShare() {
  if (state.screenActive) {
    stopMediaSharing();
    return;
  }
  stopMediaSharing();
  try {
    if (!ensureSecureMediaDevices()) return;
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { width: 1024, height: 768 },
    });
    startVideoFrameStreaming(stream, "screen");
  } catch (err) {
    logTelemetry("Ekran paylaşımı iptal edildi: " + err.message, "interrupt");
  }
}

function startVideoFrameStreaming(stream, mode) {
  state.mediaStream = stream;
  el.liveVideo.srcObject = stream;
  el.videoPreviewBox.classList.remove("hidden");
  const stageEl = document.getElementById("visualizerStage");
  if (stageEl) {
    stageEl.classList.add("video-active");
  }
  const badgeEl = document.getElementById("videoStreamBadge");

  if (mode === "camera") {
    state.cameraActive = true;
    el.liveVideo.classList.remove("screen-mode");
    el.btnCamera.classList.add("active");
    if (badgeEl) badgeEl.textContent = "📷 CANLI KAMERA GÖRÜNTÜSÜ (1 FPS ➔ Gemini 3.8 Live)";
    logTelemetry("📷 Canlı Kamera paylaşımı başlatıldı (1 FPS JPEG ➔ Gemini Live).", "success");
  } else {
    state.screenActive = true;
    el.liveVideo.classList.add("screen-mode");
    el.btnScreen.classList.add("active");
    if (badgeEl) badgeEl.textContent = "🖥️ CANLI EKRAN PAYLAŞIMI (1 FPS ➔ Gemini 3.8 Live)";
    logTelemetry("🖥️ Canlı Ekran paylaşımı başlatıldı (1 FPS JPEG ➔ Gemini Live).", "success");
  }

  const expandBtn = document.getElementById("btnToggleVideoSize");
  if (expandBtn && !expandBtn.dataset.bound) {
    expandBtn.dataset.bound = "1";
    expandBtn.addEventListener("click", () => {
      if (!stageEl) return;
      const expanded = stageEl.classList.toggle("video-expanded");
      expandBtn.textContent = expanded ? "🗗 Küçült" : "⛶ Büyüt";
    });
  }

  const ctx = el.frameCaptureCanvas.getContext("2d");
  state.frameTimer = setInterval(() => {
    if (!state.connected || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
    ctx.drawImage(el.liveVideo, 0, 0, 640, 480);
    const dataUrl = el.frameCaptureCanvas.toDataURL("image/jpeg", 0.58);
    const b64 = dataUrl.split(",")[1];
    state.ws.send(JSON.stringify({ type: "image", mime_type: "image/jpeg", data: b64 }));
  }, 1200);
}

function stopMediaSharing() {
  if (state.frameTimer) {
    clearInterval(state.frameTimer);
    state.frameTimer = null;
  }
  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach((t) => t.stop());
    state.mediaStream = null;
  }
  state.cameraActive = false;
  state.screenActive = false;
  el.btnCamera.classList.remove("active");
  el.btnScreen.classList.remove("active");
  el.videoPreviewBox.classList.add("hidden");
  const stageEl = document.getElementById("visualizerStage");
  if (stageEl) {
    stageEl.classList.remove("video-active", "video-expanded");
  }
  const expandBtn = document.getElementById("btnToggleVideoSize");
  if (expandBtn) {
    expandBtn.textContent = "⛶ Büyüt";
  }
}

// ============================================================================
// 6. DYNAMIC ADK TOOL WIDGET CARDS & GEMINI 3.8 FLASH INSIGHTS
// ============================================================================
function renderWidgetCard(widget) {
  if (!widget) return;
  const emptyCard = el.widgetsCanvas.querySelector(".empty-widget-card");
  if (emptyCard) emptyCard.remove();

  const card = document.createElement("div");
  card.className = "live-widget-card";
  const d = widget.data || {};
  let bodyHtml = "";

  if (widget.widget_type === "bank_summary") {
    const cardsHtml = Object.values(d.cards || {})
      .map(
        (c) => `
      <div class="kv-row">
        <span class="kv-key">💳 ${c.name} (*${c.last4})</span>
        <span class="kv-val">${c.status} | ${c.last_tx}</span>
      </div>`
      )
      .join("");
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Müşteri</span><span class="kv-val">${d.customer_name} (${d.segment})</span></div>
      <div class="kv-row"><span class="kv-key">Vadesiz TL / Döviz</span><span class="kv-val">${d.balance_try.toLocaleString("tr-TR")} TL / $${d.balance_usd.toLocaleString("en-US")}</span></div>
      ${cardsHtml}
    `;
  } else if (widget.widget_type === "card_security_action") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Kart</span><span class="kv-val">${d.card_name} (*${d.card_last4})</span></div>
      <div class="kv-row"><span class="kv-key">Yeni Güvenlik Durumu</span><span class="kv-val">${d.status}</span></div>
      <div class="kv-row"><span class="kv-key">Referans No</span><span class="kv-val mono">${d.case_id}</span></div>
      <div class="kv-row"><span class="kv-key">Açıklama</span><span class="kv-val">${d.reason}</span></div>
    `;
  } else if (widget.widget_type === "financial_offer") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Tutar / Vade</span><span class="kv-val">${d.amount} (${d.term})</span></div>
      <div class="kv-row"><span class="kv-key">Aylık Taksit / Net</span><span class="kv-val">${d.monthly_or_net}</span></div>
      <div class="kv-row"><span class="kv-key">Toplam</span><span class="kv-val">${d.total}</span></div>
    `;
  } else if (widget.widget_type === "order_tracking") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Ürün</span><span class="kv-val">${d.product}</span></div>
      <div class="kv-row"><span class="kv-key">Durum</span><span class="kv-val">${d.status}</span></div>
      <div class="kv-row"><span class="kv-key">Kurye / Tahmini Varış</span><span class="kv-val">${d.courier} (${d.eta})</span></div>
    `;
  } else if (widget.widget_type === "return_approved") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Sipariş &amp; Ürün</span><span class="kv-val">${d.order_id} - ${d.product}</span></div>
      <div class="kv-row"><span class="kv-key">Doğrulanan Kusur</span><span class="kv-val">${d.defect_verified}</span></div>
      <div class="kv-row"><span class="kv-key">Çözüm &amp; Kupon</span><span class="kv-val">${d.resolution} (${d.coupon_code})</span></div>
    `;
  } else if (widget.widget_type === "device_diagnostics") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Cihaz Model</span><span class="kv-val">${d.model}</span></div>
      <div class="kv-row"><span class="kv-key">Optik PON Durumu</span><span class="kv-val">${d.pon_light}</span></div>
      <div class="kv-row"><span class="kv-key">SNR / Paket Kaybı</span><span class="kv-val">${d.snr_db} dB / %${d.packet_loss_pct}</span></div>
    `;
  } else if (widget.widget_type === "clinic_slots") {
    bodyHtml = (d.slots || [])
      .map(
        (s) => `
      <div class="kv-row">
        <span class="kv-key">🩺 ${s.doctor}</span>
        <span class="kv-val">${s.time} (${s.hospital})</span>
      </div>`
      )
      .join("");
  } else if (widget.widget_type === "appointment_confirmed") {
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">Doktor &amp; Bölüm</span><span class="kv-val">${d.doctor} (${d.department})</span></div>
      <div class="kv-row"><span class="kv-key">Randevu Saati</span><span class="kv-val">${d.time_slot}</span></div>
      <div class="kv-row"><span class="kv-key">Ön-Triyaj Özeti</span><span class="kv-val">${d.symptoms}</span></div>
    `;
  } else if (widget.widget_type === "google_search_grounding") {
    const queriesStr = (d.executed_queries || [d.query]).join(" • ");
    const sourcesHtml = (d.sources || [])
      .map(
        (s) =>
          s.uri
            ? `<a href="${s.uri}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline;margin-right:8px;">🔗 ${s.title}</a>`
            : `<span style="margin-right:8px;">🔗 ${s.title}</span>`
      )
      .join(" ");
    bodyHtml = `
      <div class="kv-row"><span class="kv-key">🔍 Google Sorgusu</span><span class="kv-val mono">${queriesStr}</span></div>
      <div class="insight-pre" style="margin-top:6px;">${d.answer}</div>
      ${
        sourcesHtml
          ? `<div class="kv-row" style="margin-top:6px;"><span class="kv-key">Doğrulanan Web Kaynakları</span><span class="kv-val">${sourcesHtml}</span></div>`
          : ""
      }
    `;
  } else if (widget.widget_type === "gemini_38_insight") {
    bodyHtml = `<div class="insight-pre">${d.result}</div>`;
  } else {
    bodyHtml = `<div class="insight-pre">${JSON.stringify(d, null, 2)}</div>`;
  }

  card.innerHTML = `
    <div class="lw-header">
      <span class="lw-title">${widget.title}</span>
      <span class="lw-badge">${widget.badge}</span>
    </div>
    <div class="lw-body">${bodyHtml}</div>
  `;

  el.widgetsCanvas.prepend(card);
}

// ============================================================================
// 7. SEND PROMPTS, TEXT & 1-CLICK GEMINI 3.8 FLASH EXECUTIVE SUMMARY
// ============================================================================
async function sendSamplePrompt(promptText) {
  if (!state.connected) {
    await connectSession();
    // Wait briefly for WebSocket open
    await new Promise((r) => setTimeout(r, 600));
  }
  sendTextMessage(promptText);
}

function sendTextMessage(textVal) {
  const clean = textVal.trim();
  if (!clean) return;
  if (!state.connected || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
    connectSession().then(() => {
      setTimeout(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          stopAllAudioPlayback();
          appendTranscription("user", clean, true, "Hızlı Senaryo Komutu");
          state.ws.send(JSON.stringify({ type: "text", text: clean }));
        }
      }, 700);
    });
    return;
  }

  stopAllAudioPlayback();
  if (state.selectedModeId === "native_audio") {
    appendTranscription("user", clean, true, "Kullanıcı Mesajı");
  }
  state.ws.send(JSON.stringify({ type: "text", text: clean }));
}

el.textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const val = el.textInput.value;
  el.textInput.value = "";
  sendTextMessage(val);
});

el.btnConnect.addEventListener("click", () => connectSession());
el.btnMic.addEventListener("click", () => toggleMicrophone());
el.btnCamera.addEventListener("click", () => toggleCameraShare());
el.btnScreen.addEventListener("click", () => toggleScreenShare());
el.btnInterrupt.addEventListener("click", () => {
  stopAllAudioPlayback();
  setOrbStatus("✋ SÖZ KESİLDİ (BARGE-IN) — YENİ KOMUT BEKLENİYOR");
  logTelemetry("Kullanıcı manuel Barge-In (Söz Kesme) tetikledi.", "interrupt");
});

el.btnClearLogs.addEventListener("click", () => {
  el.telemetryLog.innerHTML = "";
});

el.btnExecSummary.addEventListener("click", async () => {
  el.btnExecSummary.textContent = "⏳ Analiz Ediliyor...";
  try {
    const res = await fetch("/api/executive-summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_id: state.selectedScenarioId,
        transcript: state.transcriptHistory,
      }),
    });
    const data = await res.json();
    if (data.ui_widget) {
      renderWidgetCard(data.ui_widget);
      logTelemetry("✨ Gemini 3.8 Flash çağrı sonu CRM & Kalite özeti oluşturuldu.", "success");
    }
  } catch (err) {
    logTelemetry("Özet hatası: " + err.message, "interrupt");
  } finally {
    el.btnExecSummary.textContent = "✨ 3.8 Flash Özeti";
  }
});

// ============================================================================
// 8. AUDIO ORB & DUAL WAVEFORM CANVAS VISUALIZER
// ============================================================================
function setOrbStatus(text) {
  state.orbStatus = text;
  el.orbStateBadge.textContent = text;
}

function logTelemetry(message, level = "info") {
  const div = document.createElement("div");
  div.className = `log-entry ${level}`;
  const now = new Date().toLocaleTimeString("tr-TR", { hour12: false });
  div.textContent = `[${now}] ${message}`;
  el.telemetryLog.prepend(div);
}

function startVisualizerAnimation() {
  const canvas = el.audioCanvas;
  const ctx = canvas.getContext("2d");
  let phase = 0;

  function draw() {
    requestAnimationFrame(draw);
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2 - 10;
    const activeEnergy = Math.max(state.micLevel, state.speakerLevel, state.connected ? 0.12 : 0.04);

    // Central Glowing Orb
    const baseRadius = 34 + activeEnergy * 26;
    const grad = ctx.createRadialGradient(cx, cy, 4, cx, cy, baseRadius * 1.45);
    if (state.speakerLevel > 0.05) {
      grad.addColorStop(0, "rgba(56, 189, 248, 0.95)");
      grad.addColorStop(0.5, "rgba(99, 102, 241, 0.55)");
      grad.addColorStop(1, "rgba(15, 23, 42, 0)");
    } else if (state.micLevel > 0.05) {
      grad.addColorStop(0, "rgba(52, 211, 153, 0.95)");
      grad.addColorStop(0.5, "rgba(16, 185, 129, 0.45)");
      grad.addColorStop(1, "rgba(15, 23, 42, 0)");
    } else {
      grad.addColorStop(0, "rgba(129, 140, 248, 0.75)");
      grad.addColorStop(0.6, "rgba(56, 189, 248, 0.22)");
      grad.addColorStop(1, "rgba(15, 23, 42, 0)");
    }

    ctx.beginPath();
    ctx.arc(cx, cy, baseRadius * 1.4, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Harmonic Waves
    const lines = 3;
    for (let j = 0; j < lines; j++) {
      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle =
        j === 0
          ? "rgba(56, 189, 248, 0.65)"
          : j === 1
          ? "rgba(129, 140, 248, 0.45)"
          : "rgba(52, 211, 153, 0.4)";

      for (let x = 30; x < w - 30; x += 4) {
        const distFromCenter = 1 - Math.abs(x - cx) / (w / 2);
        const amp = (8 + activeEnergy * 42) * Math.pow(distFromCenter, 1.6);
        const y = cy + Math.sin(x * 0.032 + phase + j * 1.3) * amp;
        if (x === 30) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    phase += 0.08 + activeEnergy * 0.14;
  }

  draw();
}

window.addEventListener("DOMContentLoaded", initStudio);
