const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

export class DebateApiError extends Error {
  constructor(message, payload = null, status = 500) {
    super(message);
    this.name = "DebateApiError";
    this.payload = payload;
    this.status = status;
  }
}

async function parseJsonSafely(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function ensureJsonResponse(response) {
  if (response.ok) {
    return response.json();
  }

  const payload = await parseJsonSafely(response);
  const message =
    payload?.error?.message || `Request failed with status ${response.status}`;

  throw new DebateApiError(message, payload, response.status);
}

export async function startDebate({
  baseUrl = DEFAULT_BASE_URL,
  topic,
  position,
  model,
}) {
  const payload = { topic, position };
  if (model) payload.model = model;

  const response = await fetch(`${baseUrl}/api/debate/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return ensureJsonResponse(response);
}

export async function evaluateDebate({
  baseUrl = DEFAULT_BASE_URL,
  sessionId,
}) {
  const response = await fetch(`${baseUrl}/api/debate/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  return ensureJsonResponse(response);
}

export async function streamDebateRound({
  baseUrl = DEFAULT_BASE_URL,
  sessionId,
  content,
  onChunk,
  onDone,
  onError,
}) {
  const response = await fetch(`${baseUrl}/api/debate/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      content,
    }),
  });

  if (!response.ok || !response.body) {
    const payload = await parseJsonSafely(response);
    const message =
      payload?.error?.message ||
      `Stream request failed with status ${response.status}`;

    throw new DebateApiError(message, payload, response.status);
  }

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
      const lines = rawEvent.split("\n");
      const eventName = lines
        .find((line) => line.startsWith("event: "))
        ?.replace("event: ", "")
        .trim();
      const dataText = lines
        .find((line) => line.startsWith("data: "))
        ?.replace("data: ", "");

      if (!eventName || !dataText) continue;

      const payload = JSON.parse(dataText);

      if (eventName === "chunk") {
        onChunk?.(payload);
      }

      if (eventName === "done") {
        onDone?.(payload);
      }

      if (eventName === "error") {
        onError?.(payload);
      }
    }
  }
}

export async function runDebateRoundAndMaybeEvaluate({
  baseUrl = DEFAULT_BASE_URL,
  sessionId,
  content,
  onChunk,
  onRoundDone,
  onStreamError,
}) {
  let finalRoundPayload = null;

  await streamDebateRound({
    baseUrl,
    sessionId,
    content,
    onChunk,
    onDone(payload) {
      finalRoundPayload = payload;
      onRoundDone?.(payload);
    },
    onError(payload) {
      onStreamError?.(payload);
    },
  });

  if (finalRoundPayload?.is_final_round) {
    return evaluateDebate({ baseUrl, sessionId });
  }

  return null;
}
