(function (global) {
  "use strict";

  const DEFAULT_BASE = "";
  const VALID_STATUSES = ["submitted", "acknowledged", "in_progress", "resolved", "rejected"];

  function baseUrl() {
    const configured = global.CIVICSIGNAL_API_BASE;
    return String(configured == null ? DEFAULT_BASE : configured).replace(/\/+$/, "");
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body != null) headers.set("Content-Type", "application/json");

    let response;
    try {
      response = await fetch(`${baseUrl()}${path}`, {
        ...options,
        headers,
        credentials: "same-origin",
      });
    } catch {
      throw new Error("Could not reach the server. Check your connection and try again.");
    }

    const contentType = response.headers.get("content-type") || "";
    let payload = null;
    if (response.status !== 204) {
      if (contentType.includes("application/json")) {
        try {
          payload = await response.json();
        } catch {
          throw new Error("The server returned an invalid JSON response.");
        }
      } else {
        const bodyText = await response.text();
        if (bodyText) payload = { detail: bodyText };
      }
    }

    if (!response.ok) {
      const detail = payload && (payload.detail || payload.message);
      const message = typeof detail === "string" ? detail : detail && detail.message;
      const error = new Error(message || `Request failed (HTTP ${response.status}).`);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function normalizeReport(report) {
    if (!report || typeof report !== "object") throw new Error("The server returned an invalid report.");
    if (!report.id) throw new Error("The report response is missing its id.");
    if (!report.status || !VALID_STATUSES.includes(report.status)) {
      throw new Error("The report response contains an unsupported status.");
    }
    return report;
  }

  const api = {
    statuses: VALID_STATUSES.slice(),

    async listReports() {
      const data = await request("/api/reports");
      const reports = Array.isArray(data) ? data : data && data.reports;
      if (!Array.isArray(reports)) throw new Error("The reports response must contain a reports array.");
      return reports.map(normalizeReport);
    },

    async listMyReports() {
      const data = await request("/api/reports/mine");
      if (!data || !Array.isArray(data.reports)) throw new Error("The reports response is invalid.");
      return data.reports.map(normalizeReport);
    },

    async updateStatus(id, status, message = "") {
      if (!VALID_STATUSES.includes(status)) throw new Error("Choose a valid report status.");
      return await request(`/api/team/reports/${encodeURIComponent(id)}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, message }),
      });
    },

    async updateReport(id, status, message, files, onProgress) {
      const body = new FormData();
      if (status) body.append("status", status);
      body.append("message", message || "");
      files.forEach((file) => body.append("files", file, file.name));
      return await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${baseUrl()}/api/team/reports/${encodeURIComponent(id)}/updates`);
        xhr.withCredentials = true;
        xhr.setRequestHeader("Accept", "application/json");
        xhr.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable && onProgress) onProgress(Math.round(event.loaded / event.total * 100));
        });
        xhr.addEventListener("load", () => {
          let payload;
          try { payload = JSON.parse(xhr.responseText); } catch { payload = {}; }
          if (xhr.status >= 200 && xhr.status < 300) resolve(payload);
          else {
            const error = new Error(payload.detail || `Request failed (HTTP ${xhr.status}).`);
            error.status = xhr.status;
            reject(error);
          }
        });
        xhr.addEventListener("error", () => reject(new Error("Could not reach the server.")));
        xhr.send(body);
      });
    },

    async logout() {
      return await request("/api/auth/team/logout", { method: "POST" });
    },

    async getTracking(id) {
      const data = await request(`/api/reports/${encodeURIComponent(id)}/tracking`);
      if (!data || typeof data !== "object") throw new Error("The tracking response is invalid.");
      const report = normalizeReport(data.report || data);
      const timeline = Array.isArray(data.timeline) ? data.timeline : [];
      const images = Array.isArray(data.images) ? data.images : [];
      return { report, timeline, images };
    },
  };

  global.CivicSignalAPI = api;
})(window);
