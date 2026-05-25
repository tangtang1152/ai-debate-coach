const MAX_ROUNDS = 3;
const STORAGE_KEY = "argument-arena-api-base";
const LAST_SESSION_KEY = "argument-arena-last-session";
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free";
const TYPEWRITER_DELAY_MS = 18;

const modelLabels = {
  "qwen/qwen3-next-80b-a3b-instruct:free": "Qwen 默认模型",
  "tencent/hy3-preview:free": "Tencent Hunyuan",
  "google/gemma-4-31b-it:free": "Google Gemma",
  "qwen/qwen3-coder:free": "Qwen Coder",
};

const phaseText = {
  setup: "待开始",
  created: "等待发言",
  streaming: "AI 生成中",
  waiting_next_round: "等待下一轮",
  ready_for_evaluation: "等待评分",
  evaluating: "评分生成中",
  finished: "已完成",
  error: "需要处理",
};

const els = {
  apiBaseUrl: document.querySelector("#apiBaseUrl"),
  setupForm: document.querySelector("#setupForm"),
  topicInput: document.querySelector("#topicInput"),
  modelSelect: document.querySelector("#modelSelect"),
  startButton: document.querySelector("#startButton"),
  resetButton: document.querySelector("#resetButton"),
  refreshHistoryButton: document.querySelector("#refreshHistoryButton"),
  exampleTopics: document.querySelectorAll("[data-topic]"),
  sessionMeta: document.querySelector("#sessionMeta"),
  phaseMeta: document.querySelector("#phaseMeta"),
  modelMeta: document.querySelector("#modelMeta"),
  debateContext: document.querySelector("#debateContext"),
  messageList: document.querySelector("#messageList"),
  messageForm: document.querySelector("#messageForm"),
  messageInput: document.querySelector("#messageInput"),
  sendButton: document.querySelector("#sendButton"),
  retryButton: document.querySelector("#retryButton"),
  roundLabel: document.querySelector("#roundLabel"),
  roundProgress: document.querySelector("#roundProgress"),
  reportBadge: document.querySelector("#reportBadge"),
  logicScore: document.querySelector("#logicScore"),
  evidenceScore: document.querySelector("#evidenceScore"),
  fluencyScore: document.querySelector("#fluencyScore"),
  suggestionText: document.querySelector("#suggestionText"),
  radarShape: document.querySelector("#radarShape"),
  evaluateButton: document.querySelector("#evaluateButton"),
  historyList: document.querySelector("#historyList"),
  toast: document.querySelector("#toast"),
};

const state = {
  sessionId: "",
  topic: "",
  position: "正方",
  model: DEFAULT_MODEL,
  currentRound: 0,
  phase: "setup",
  messages: [],
  evaluation: null,
  sessions: [],
  historyLoading: false,
  lastRoundContent: "",
  lastAssistantId: "",
};

function uid(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getApiBaseUrl() {
  return els.apiBaseUrl.value.trim().replace(/\/$/, "");
}

function setPhase(phase) {
  state.phase = phase;
  render();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.classList.add("hidden");
  }, 3200);
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function getSelectedPosition() {
  return new FormData(els.setupForm).get("position") || "正方";
}

function getSelectedModel() {
  return els.modelSelect.value || DEFAULT_MODEL;
}

function getModelLabel(model) {
  return modelLabels[model] || model || "未设置";
}

function validateTopic(topic) {
  if (!topic) return "请输入辩题。";
  if (topic.length > 100) return "辩题长度不能超过 100 字。";
  return "";
}

function validateContent(content) {
  if (!content) return "请输入本轮观点。";
  if (content.length < 5) return "本轮观点可以再具体一点。";
  if (content.length > 1200) return "本轮观点建议控制在 1200 字以内。";
  return "";
}

function resetSession() {
  window.localStorage.removeItem(LAST_SESSION_KEY);
  state.sessionId = "";
  state.topic = "";
  state.position = getSelectedPosition();
  state.model = getSelectedModel();
  state.currentRound = 0;
  state.phase = "setup";
  state.messages = [];
  state.evaluation = null;
  state.lastRoundContent = "";
  state.lastAssistantId = "";
  els.messageInput.value = "";
  render();
}

function applySessionDetail(session) {
  state.sessionId = session.session_id;
  state.topic = session.topic;
  state.position = session.position;
  state.model = session.model || DEFAULT_MODEL;
  state.currentRound = session.current_round;
  state.messages = (session.messages || []).map((message) => ({
    id: `saved-${message.id}`,
    role: message.role,
    roundNo: message.round_no,
    content: message.content,
    status: "done",
  }));
  state.evaluation = session.evaluation
    ? {
        logicScore: session.evaluation.logic_score,
        evidenceScore: session.evaluation.evidence_score,
        fluencyScore: session.evaluation.fluency_score,
        suggestion: session.evaluation.suggestion,
        fallbackUsed: false,
        cached: true,
      }
    : null;
  state.lastRoundContent = "";
  state.lastAssistantId = "";
  state.phase = getRestoredPhase();
  els.topicInput.value = state.topic;
  els.modelSelect.value = state.model;
  els.setupForm
    .querySelectorAll('input[name="position"]')
    .forEach((input) => {
      input.checked = input.value === state.position;
    });
  window.localStorage.setItem(LAST_SESSION_KEY, state.sessionId);
}

function getRestoredPhase() {
  if (state.evaluation) return "finished";
  if (state.currentRound >= MAX_ROUNDS) return "ready_for_evaluation";
  if (state.currentRound > 0) return "waiting_next_round";
  return "created";
}

async function startDebate(topic, position, model) {
  const response = await fetch(`${getApiBaseUrl()}/api/debate/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ topic, position, model }),
  });

  return ensureJsonResponse(response);
}

async function fetchRecentSessions() {
  const response = await fetch(`${getApiBaseUrl()}/api/debate/sessions`);
  return ensureJsonResponse(response);
}

async function fetchSessionDetail(sessionId) {
  const response = await fetch(`${getApiBaseUrl()}/api/debate/sessions/${sessionId}`);
  return ensureJsonResponse(response);
}

async function evaluateDebate(sessionId) {
  const response = await fetch(`${getApiBaseUrl()}/api/debate/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  return ensureJsonResponse(response);
}

async function streamDebateRound({ sessionId, content, onChunk, onDone, onError }) {
  const response = await fetch(`${getApiBaseUrl()}/api/debate/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId, content }),
  });

  if (!response.ok || !response.body) {
    const payload = await parseJsonSafely(response);
    const message =
      payload?.error?.message || `流式请求失败：HTTP ${response.status}`;
    throw new Error(message);
  }

  await readSseStream(response, { onChunk, onDone, onError });
}

async function parseJsonSafely(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function ensureJsonResponse(response) {
  if (response.ok) return response.json();

  const payload = await parseJsonSafely(response);
  const message = payload?.error?.message || `请求失败：HTTP ${response.status}`;
  throw new Error(message);
}

async function readSseStream(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const rawEvents = buffer.split("\n\n");
    buffer = rawEvents.pop() || "";

    for (const rawEvent of rawEvents) {
      const eventName = rawEvent
        .split("\n")
        .find((line) => line.startsWith("event: "))
        ?.replace("event: ", "")
        .trim();
      const dataText = rawEvent
        .split("\n")
        .find((line) => line.startsWith("data: "))
        ?.replace("data: ", "");

      if (!eventName || !dataText) continue;

      const payload = JSON.parse(dataText);
      if (eventName === "chunk") handlers.onChunk?.(payload);
      if (eventName === "done") handlers.onDone?.(payload);
      if (eventName === "error") handlers.onError?.(payload);
    }
  }
}

async function handleSetupSubmit(event) {
  event.preventDefault();

  const topic = els.topicInput.value.trim();
  const position = getSelectedPosition();
  const model = getSelectedModel();
  const error = validateTopic(topic);
  if (error) {
    showToast(error);
    return;
  }

  setPhase("created");
  els.startButton.disabled = true;

  try {
    const session = await startDebate(topic, position, model);
    state.sessionId = session.session_id;
    state.topic = session.topic;
    state.position = session.position;
    state.model = session.model || model;
    state.currentRound = session.current_round;
    state.phase = "created";
    window.localStorage.setItem(LAST_SESSION_KEY, session.session_id);
    showToast("会话已创建。");
    loadRecentSessions();
  } catch (err) {
    state.phase = "setup";
    showToast(err.message || "创建会话失败。");
  } finally {
    render();
  }
}

async function loadRecentSessions() {
  state.historyLoading = true;
  renderHistory();

  try {
    const data = await fetchRecentSessions();
    state.sessions = data.sessions || [];
  } catch (err) {
    showToast(err.message || "历史会话加载失败。");
  } finally {
    state.historyLoading = false;
    renderHistory();
  }
}

async function restoreSession(sessionId, { silent = false } = {}) {
  if (!sessionId) return;

  try {
    const session = await fetchSessionDetail(sessionId);
    applySessionDetail(session);
    if (!silent) showToast("已恢复历史会话。");
  } catch (err) {
    if (window.localStorage.getItem(LAST_SESSION_KEY) === sessionId) {
      window.localStorage.removeItem(LAST_SESSION_KEY);
    }
    if (!silent) showToast(err.message || "会话恢复失败。");
  } finally {
    render();
  }
}

async function handleMessageSubmit(event) {
  event.preventDefault();
  const content = els.messageInput.value.trim();
  const error = validateContent(content);
  if (error) {
    showToast(error);
    return;
  }

  await runRound(content, { appendUser: true });
}

async function retryLastRound() {
  if (!state.lastRoundContent) return;

  state.messages = state.messages.filter((message) => message.id !== state.lastAssistantId);
  await runRound(state.lastRoundContent, { appendUser: false });
}

async function runRound(content, { appendUser }) {
  if (!state.sessionId) {
    showToast("请先创建会话。");
    return;
  }

  if (state.currentRound >= MAX_ROUNDS) {
    showToast("三轮辩论已完成。");
    return;
  }

  const roundNo = state.currentRound + 1;
  const assistantId = uid("assistant");
  state.lastRoundContent = content;
  state.lastAssistantId = assistantId;

  if (appendUser) {
    state.messages.push({
      id: uid("user"),
      role: "user",
      roundNo,
      content,
      status: "done",
    });
  }

  state.messages.push({
    id: assistantId,
    role: "assistant",
    roundNo,
    content: "",
    status: "streaming",
  });

  els.messageInput.value = "";
  setPhase("streaming");
  scrollMessagesToBottom();

  const typewriter = createTypewriter(assistantId);
  let donePayload = null;

  try {
    await streamDebateRound({
      sessionId: state.sessionId,
      content,
      onChunk(payload) {
        typewriter.enqueue(payload.content);
      },
      onDone(payload) {
        donePayload = payload;
      },
      onError(payload) {
        throwStreamError(assistantId, payload.message);
      },
    });

    await typewriter.flush();

    if (donePayload) {
      markAssistantDone(assistantId);
      state.currentRound = donePayload.current_round;
      state.phase = donePayload.is_final_round ? "evaluating" : "waiting_next_round";
      render();
    }

    if (state.phase === "evaluating") {
      await generateEvaluation();
    }
  } catch (err) {
    typewriter.stop();
    markAssistantError(assistantId, err.message || "流式生成失败，请重试。");
    state.phase = "error";
    showToast(err.message || "流式生成失败，请重试。");
    render();
  }
}

function throwStreamError(assistantId, message) {
  markAssistantError(assistantId, message || "流式生成失败，请重试。");
  throw new Error(message || "流式生成失败，请重试。");
}

function appendAssistantChunk(messageId, content) {
  const message = state.messages.find((item) => item.id === messageId);
  if (!message) return;
  message.content += content;
  renderMessages();
  scrollMessagesToBottom();
}

function createTypewriter(messageId) {
  const queue = [];
  const flushResolvers = [];
  let active = false;
  let stopped = false;

  function resolveFlushIfIdle() {
    if (active || queue.length) return;
    while (flushResolvers.length) {
      flushResolvers.shift()();
    }
  }

  async function pump() {
    if (active) return;
    active = true;

    while (queue.length && !stopped) {
      appendAssistantChunk(messageId, queue.shift());
      await sleep(TYPEWRITER_DELAY_MS);
    }

    active = false;
    resolveFlushIfIdle();
  }

  return {
    enqueue(content) {
      if (stopped || !content) return;
      queue.push(...Array.from(content));
      pump();
    },
    flush() {
      if (!active && !queue.length) return Promise.resolve();
      return new Promise((resolve) => {
        flushResolvers.push(resolve);
        resolveFlushIfIdle();
      });
    },
    stop() {
      stopped = true;
      queue.length = 0;
      resolveFlushIfIdle();
    },
  };
}

function markAssistantDone(messageId) {
  const message = state.messages.find((item) => item.id === messageId);
  if (message) message.status = "done";
}

function markAssistantError(messageId, messageText) {
  const message = state.messages.find((item) => item.id === messageId);
  if (!message) return;
  message.status = "error";
  if (!message.content.trim()) message.content = messageText;
}

async function generateEvaluation() {
  if (!state.sessionId) return;

  setPhase("evaluating");

  try {
    const result = await evaluateDebate(state.sessionId);
    state.evaluation = {
      logicScore: result.logic_score,
      evidenceScore: result.evidence_score,
      fluencyScore: result.fluency_score,
      suggestion: result.suggestion,
      fallbackUsed: result.fallback_used,
      cached: result.cached,
    };
    state.phase = "finished";
    showToast("评分已生成。");
  } catch (err) {
    state.phase = "error";
    showToast(err.message || "评分生成失败。");
  } finally {
    render();
  }
}

function render() {
  renderMeta();
  renderSetup();
  renderDebateHeader();
  renderMessages();
  renderComposer();
  renderReport();
  renderHistory();
}

function renderMeta() {
  els.sessionMeta.textContent = state.sessionId || "未创建";
  els.phaseMeta.textContent = phaseText[state.phase] || "待开始";
  els.modelMeta.textContent = getModelLabel(state.model);
}

function renderSetup() {
  const isBusy = state.phase === "streaming" || state.phase === "evaluating";
  const hasActiveSession = Boolean(state.sessionId);
  els.startButton.disabled = isBusy || hasActiveSession;
  els.topicInput.disabled = isBusy || hasActiveSession;
  els.modelSelect.disabled = isBusy || hasActiveSession;
  els.setupForm
    .querySelectorAll('input[name="position"]')
    .forEach((input) => {
      input.disabled = isBusy || hasActiveSession;
    });
}

function renderDebateHeader() {
  els.roundLabel.textContent = `${state.currentRound} / ${MAX_ROUNDS}`;
  els.roundProgress.style.width = `${(state.currentRound / MAX_ROUNDS) * 100}%`;

  if (!state.topic) {
    els.debateContext.textContent = "辩题未设置";
    return;
  }

  const assistantPosition = state.position === "正方" ? "反方" : "正方";
  els.debateContext.textContent =
    `辩题：${state.topic}｜你方：${state.position}｜AI：${assistantPosition}｜模型：${getModelLabel(state.model)}`;
}

function renderMessages() {
  if (!state.messages.length) {
    els.messageList.innerHTML = `
      <div class="empty-state">
        <strong>等待开场</strong>
        <span>创建会话后提交第一轮观点。</span>
      </div>
    `;
    return;
  }

  els.messageList.innerHTML = state.messages
    .map((message) => {
      const roleLabel = message.role === "user" ? "你" : "AI";
      const statusLabel = getMessageStatusLabel(message);
      const caretClass =
        message.role === "assistant" && message.status === "streaming"
          ? "typing-caret"
          : "";

      return `
        <div class="message-row ${message.role} ${message.status}">
          <article class="message-bubble">
            <div class="bubble-meta">
              <span>${roleLabel} · 第 ${message.roundNo} 回合</span>
              <span>${statusLabel}</span>
            </div>
            <div class="${caretClass}">${escapeHtml(message.content || "正在组织反驳...")}</div>
          </article>
        </div>
      `;
    })
    .join("");
}

function getMessageStatusLabel(message) {
  if (message.status === "streaming") return "生成中";
  if (message.status === "error") return "失败";
  return "完成";
}

function renderComposer() {
  const canSend =
    state.sessionId &&
    state.currentRound < MAX_ROUNDS &&
    !["streaming", "evaluating", "finished"].includes(state.phase);

  els.messageInput.disabled = !canSend;
  els.sendButton.disabled = !canSend;
  els.retryButton.classList.toggle("hidden", state.phase !== "error" || !state.lastRoundContent);
}

function renderReport() {
  const isReady = Boolean(state.evaluation);
  const canManualEvaluate = state.sessionId && state.currentRound >= MAX_ROUNDS && !isReady;

  els.evaluateButton.disabled = !canManualEvaluate || state.phase === "evaluating";
  els.evaluateButton.textContent =
    state.phase === "evaluating" ? "生成中" : "生成评分";

  els.reportBadge.classList.toggle("ready", isReady);
  els.reportBadge.classList.toggle("warning", Boolean(state.evaluation?.fallbackUsed));

  if (!isReady) {
    els.reportBadge.textContent = state.phase === "evaluating" ? "生成中" : "未生成";
    els.logicScore.textContent = "--";
    els.evidenceScore.textContent = "--";
    els.fluencyScore.textContent = "--";
    els.suggestionText.textContent = "完成三轮辩论后生成。";
    updateRadar([0, 0, 0]);
    return;
  }

  els.reportBadge.textContent = state.evaluation.fallbackUsed ? "降级评分" : "已生成";
  els.logicScore.textContent = state.evaluation.logicScore;
  els.evidenceScore.textContent = state.evaluation.evidenceScore;
  els.fluencyScore.textContent = state.evaluation.fluencyScore;
  els.suggestionText.textContent = state.evaluation.suggestion;
  updateRadar([
    state.evaluation.logicScore,
    state.evaluation.evidenceScore,
    state.evaluation.fluencyScore,
  ]);
}

function renderHistory() {
  if (state.historyLoading) {
    els.historyList.innerHTML = `<p class="history-empty">正在加载...</p>`;
    return;
  }

  if (!state.sessions.length) {
    els.historyList.innerHTML = `<p class="history-empty">暂无历史会话</p>`;
    return;
  }

  els.historyList.innerHTML = state.sessions
    .map((session) => {
      const activeClass = session.session_id === state.sessionId ? "active" : "";
      const status = session.has_evaluation
        ? "已评分"
        : `${session.current_round} / ${MAX_ROUNDS} 回合`;
      return `
        <button class="history-item ${activeClass}" type="button" data-session-id="${session.session_id}">
          <span>${escapeHtml(session.topic)}</span>
          <small>${escapeHtml(session.position)} · ${status}</small>
        </button>
      `;
    })
    .join("");

  els.historyList.querySelectorAll("[data-session-id]").forEach((button) => {
    button.addEventListener("click", () => {
      restoreSession(button.dataset.sessionId);
    });
  });
}

function updateRadar(scores) {
  const center = { x: 120, y: 120 };
  const vertices = [
    { x: 120, y: 20 },
    { x: 206.6, y: 170 },
    { x: 33.4, y: 170 },
  ];
  const points = vertices
    .map((vertex, index) => {
      const ratio = Math.max(0, Math.min(10, scores[index])) / 10;
      const x = center.x + (vertex.x - center.x) * ratio;
      const y = center.y + (vertex.y - center.y) * ratio;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  els.radarShape.setAttribute("points", points);
}

function scrollMessagesToBottom() {
  requestAnimationFrame(() => {
    els.messageList.scrollTop = els.messageList.scrollHeight;
  });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  els.setupForm.addEventListener("submit", handleSetupSubmit);
  els.messageForm.addEventListener("submit", handleMessageSubmit);
  els.retryButton.addEventListener("click", retryLastRound);
  els.resetButton.addEventListener("click", resetSession);
  els.refreshHistoryButton.addEventListener("click", loadRecentSessions);
  els.evaluateButton.addEventListener("click", generateEvaluation);

  els.exampleTopics.forEach((button) => {
    button.addEventListener("click", () => {
      els.topicInput.value = button.dataset.topic;
      els.topicInput.focus();
    });
  });

  els.apiBaseUrl.addEventListener("change", () => {
    window.localStorage.setItem(STORAGE_KEY, getApiBaseUrl());
  });

  els.modelSelect.addEventListener("change", () => {
    if (!state.sessionId) {
      state.model = getSelectedModel();
      renderMeta();
    }
  });
}

function init() {
  const storedApiBase = window.localStorage.getItem(STORAGE_KEY);
  if (
    storedApiBase &&
    ![
      "http://127.0.0.1:5000",
      "http://localhost:5000",
      "http://127.0.0.1:5001",
      "http://localhost:5001",
    ].includes(storedApiBase)
  ) {
    els.apiBaseUrl.value = storedApiBase;
  } else {
    els.apiBaseUrl.value = DEFAULT_API_BASE_URL;
    window.localStorage.setItem(STORAGE_KEY, DEFAULT_API_BASE_URL);
  }
  bindEvents();
  state.model = getSelectedModel();
  render();
  loadRecentSessions().then(() => {
    const lastSessionId = window.localStorage.getItem(LAST_SESSION_KEY);
    if (lastSessionId) restoreSession(lastSessionId, { silent: true });
  });
}

init();
