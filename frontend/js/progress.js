/**
 * Module to handle real-time download progress tracking with dual-mode:
 * Server-Sent Events (SSE) + fallback polling to guarantee 100% responsiveness.
 */

export class ProgressTracker {
  constructor(taskId, { onProgress, onComplete, onError, onCancel }) {
    this.taskId = taskId;
    this.onProgress = onProgress || (() => {});
    this.onComplete = onComplete || (() => {});
    this.onError = onError || (() => {});
    this.onCancel = onCancel || (() => {});
    this.eventSource = null;
    this.pollInterval = null;
    this.isFinished = false;
  }

  handleUpdate(data) {
    if (this.isFinished) return;

    if (data.error) {
      this.isFinished = true;
      this.onError(data.error);
      this.close();
      return;
    }

    this.onProgress(data);

    if (data.status === "completed") {
      this.isFinished = true;
      this.onComplete(data);
      this.close();
    } else if (data.status === "error" || data.status === "failed") {
      this.isFinished = true;
      this.onError(data.error_message || "An error occurred during download.");
      this.close();
    } else if (data.status === "cancelled") {
      this.isFinished = true;
      this.onCancel(data);
      this.close();
    }
  }

  start() {
    this.close();
    this.isFinished = false;

    // 1. Setup Server-Sent Events with auth token query param
    const token = window.__AUTH_TOKEN__ || "";
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
    const url = `/api/progress/${encodeURIComponent(this.taskId)}${tokenParam}`;
    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onmessage = (event) => {
        try {
          let raw = event.data;
          if (typeof raw === "string") {
            // Strip any accidental leading data: prefix
            raw = raw.replace(/^data:\s*/, "").trim();
          }
          const data = JSON.parse(raw);
          this.handleUpdate(data);
        } catch (err) {
          console.error("Failed to parse SSE payload:", err, event.data);
        }
      };

      this.eventSource.onerror = (err) => {
        // SSE connection dropped; fallback polling keeps progress alive seamlessly
        console.warn("SSE stream notice:", err);
      };
    } catch (e) {
      console.warn("EventSource initialization failed, using polling mode:", e);
    }

    // 2. Setup Fallback Polling (polls every 500ms) with auth header
    this.pollInterval = setInterval(async () => {
      if (this.isFinished) {
        clearInterval(this.pollInterval);
        return;
      }

      try {
        const headers = {};
        if (window.__AUTH_TOKEN__) {
          headers["X-Auth-Token"] = window.__AUTH_TOKEN__;
        }
        const response = await fetch(`/api/status/${encodeURIComponent(this.taskId)}`, { headers });
        if (!response.ok) return;
        const data = await response.json();
        this.handleUpdate(data);
      } catch (err) {
        // Ignore polling fetch hiccups
      }
    }, 500);
  }

  close() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}
