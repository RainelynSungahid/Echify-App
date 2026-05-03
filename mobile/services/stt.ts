// stt.ts
let sttSocket: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let sttMessageCallback: ((data: any) => void) | null = null;

let pendingStart = false;

const getSttWsUrl = () => {
  const host =
    typeof window !== "undefined" ? window.location.hostname : "localhost";

  return `ws://${host}:8000/ws/stt-live`;
};

export const connectSttSocket = (onMessage: (data: any) => void) => {
  sttMessageCallback = onMessage;

  if (sttSocket && sttSocket.readyState === WebSocket.OPEN) return;
  if (sttSocket && sttSocket.readyState === WebSocket.CONNECTING) return;

  const WS_URL = getSttWsUrl();
  console.log("🎤 Connecting STT WebSocket:", WS_URL);

  sttSocket = new WebSocket(WS_URL);

  sttSocket.onopen = () => {
    console.log("✅ STT WebSocket connected");

    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }

    if (pendingStart) {
      console.log("🎤 Sending deferred START to STT");
      sttSocket?.send(JSON.stringify({ action: "start" }));
      pendingStart = false;
    }
  };

  sttSocket.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);

      if (sttMessageCallback) {
        sttMessageCallback(data);
      }
    } catch (err) {
      console.log("STT socket parse error:", err);
    }
  };

  sttSocket.onerror = () => {
    console.log("❌ STT WebSocket error");
  };

  sttSocket.onclose = () => {
    console.log("🔌 STT WebSocket closed");
    sttSocket = null;

    if (!reconnectTimeout && sttMessageCallback) {
      reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;

        if (sttMessageCallback) {
          connectSttSocket(sttMessageCallback);
        }
      }, 3000);
    }
  };
};

export const startSttListening = () => {
  if (!sttSocket) {
    console.log("⚠️ STT socket not created yet, queue START");
    pendingStart = true;
    return;
  }

  if (sttSocket.readyState === WebSocket.OPEN) {
    console.log("🎤 Sending START to STT");
    sttSocket.send(JSON.stringify({ action: "start" }));
    pendingStart = false;
    return;
  }

  if (sttSocket.readyState === WebSocket.CONNECTING) {
    console.log("⏳ STT socket still connecting, queue START");
    pendingStart = true;
  }
};

export const closeSttSocket = () => {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
  }

  reconnectTimeout = null;
  pendingStart = false;
  sttMessageCallback = null;

  sttSocket?.close();
  sttSocket = null;
};