(function () {
  "use strict";
  const api = window.CivicSignalAPI;
  const form = document.querySelector("#tracking-form");
  const input = document.querySelector("#report-id");
  const state = document.querySelector("#tracking-state");
  const result = document.querySelector("#tracking-result");
  const myReportList = document.querySelector("#my-report-list");
  const myReportsState = document.querySelector("#my-reports-state");
  const refreshMyReports = document.querySelector("#refresh-my-reports");
  if (!api || !form || !input || !state || !result) return;

  const labels = {
    submitted: "Submitted",
    acknowledged: "Under review",
    in_progress: "In progress",
    resolved: "Resolved",
    rejected: "Rejected",
  };
  const descriptions = {
    submitted: "Your report has been received.",
    acknowledged: "Your report has been acknowledged.",
    in_progress: "Work on this issue is in progress.",
    resolved: "The issue has been marked as resolved.",
  };
  const orderedStatuses = ["submitted", "acknowledged", "in_progress", "resolved"];

  function node(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
  }

  function setState(message, kind = "info") {
    state.textContent = message;
    state.className = `notice notice--${kind}`;
    state.hidden = !message;
  }

  function dateText(value) {
    if (!value) return "Date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  function render(data) {
    result.replaceChildren();
    const report = data.report;
    const summary = node("section", "tracking-summary");
    const heading = node("div", "tracking-summary__header");
    heading.append(node("h2", "", `Report ${report.id}`));
    heading.append(node("span", `status-badge status-badge--${report.status}`, labels[report.status] || report.status));
    summary.append(heading);

    if (report.title) summary.append(node("p", "report-card__title", report.title));
    if (report.category) summary.append(node("p", "report-card__meta", `Category: ${report.category}`));
    if (report.area) summary.append(node("p", "report-card__meta", `Area: ${report.area}`));
    if (report.landmark) summary.append(node("p", "report-card__meta", `Location: ${report.landmark}`));
    if (report.latitude != null && report.longitude != null) {
      const mapLink = node("a", "report-card__meta", `Map: ${Number(report.latitude).toFixed(6)}, ${Number(report.longitude).toFixed(6)}`);
      mapLink.href = `https://www.openstreetmap.org/?mlat=${encodeURIComponent(report.latitude)}&mlon=${encodeURIComponent(report.longitude)}#map=17/${encodeURIComponent(report.latitude)}/${encodeURIComponent(report.longitude)}`;
      mapLink.target = "_blank";
      mapLink.rel = "noopener noreferrer";
      summary.append(mapLink);
      if (window.L) {
        const map = node("div", "tracking-map");
        map.setAttribute("role", "application");
        map.setAttribute("aria-label", "Map of reported issue location");
        summary.append(map);
        const point = [Number(report.latitude), Number(report.longitude)];
        const issueMap = L.map(map).setView(point, 16);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        }).addTo(issueMap);
        L.marker(point).addTo(issueMap);
      }
    }
    if (report.description) summary.append(node("p", "report-card__description", report.description));
    summary.append(node("p", "report-card__meta", `Last updated: ${dateText(report.updated_at || report.created_at)}`));

    if (report.status === "resolved" && report.resolution_note) {
      summary.append(node("p", "report-card__meta", `Resolution note: ${report.resolution_note}`));
    }
    if (report.status === "rejected" && report.resolution_note) {
      summary.append(node("p", "report-card__meta", `Rejection reason: ${report.resolution_note}`));
    }

    result.append(summary);

    if (data.images?.length) {
      const gallery = node("section", "evidence-gallery");
      gallery.append(node("h2", "", "Report photos and progress evidence"));
      const grid = node("div", "evidence-gallery__grid");
      data.images.forEach((image) => {
        const figure = node("figure", "evidence-gallery__item");
        const photo = document.createElement("img");
        photo.src = image.url;
        photo.alt = image.media_type === "original" ? "Original report photo" : "Administrator progress photo";
        figure.append(photo);
        figure.append(node("figcaption", "", image.media_type === "original" ? "Original report image" : "Progress update"));
        grid.append(figure);
      });
      gallery.append(grid);
      result.append(gallery);
    }

    const timelineSection = node("section", "timeline-section");
    timelineSection.append(node("h2", "", "Status timeline"));
    const timeline = node("ol", "timeline");
    const events = [...(data.timeline || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    if (!events.length) {
      timeline.append(node("li", "empty-state", "No timeline events are available yet."));
    } else {
      events.forEach((event) => {
        const status = event.status_to || event.status || (event.event_type === "created" ? "submitted" : "");
        const item = node("li", "timeline__item");
        item.append(node("span", "timeline__marker", ""));
        const content = node("div", "timeline__content");
        const title = event.message?.startsWith("Report rejected:") ? "Rejected" : labels[status] || (event.event_type || "Update").replaceAll("_", " ");
        content.append(node("h3", "timeline__title", title));
        content.append(node("p", "timeline__date", dateText(event.created_at)));
        const note = event.message || event.note || event.evidence_note || descriptions[status] || "";
        if (note) content.append(node("p", "timeline__note", note));
        item.append(content);
        timeline.append(item);
      });
    }

    timelineSection.append(timeline);
    result.append(timelineSection);

    const currentIndex = orderedStatuses.indexOf(report.status);
    const progress = node("section", "progress-section");
    progress.append(node("h2", "", "Current progress"));
    const progressList = node("ol", "progress-list");
    orderedStatuses.forEach((status, index) => {
      const item = node("li", `progress-list__item${index <= currentIndex ? " is-reached" : ""}`);
      const step = node("span", "progress-list__label", labels[status]);
      const detail = node("small", "progress-list__note", descriptions[status]);
      item.append(step, detail);
      progressList.append(item);
    });
    progress.append(progressList);
    result.append(progress);
  }

  async function loadMyReports() {
    if (!myReportList || !myReportsState) return;
    myReportList.replaceChildren();
    myReportsState.textContent = "Loading your reports…";
    myReportsState.hidden = false;
    if (refreshMyReports) refreshMyReports.disabled = true;
    try {
      const reports = await api.listMyReports();
      myReportsState.textContent = reports.length ? `${reports.length} report(s) found.` : "You have not submitted any reports yet.";
      reports.forEach((report) => {
        const card = node("article", "my-report-card");
        const heading = node("div", "my-report-card__heading");
        heading.append(node("strong", "", report.title || `Report ${report.id}`));
        heading.append(node("span", `status-badge status-badge--${report.status}`, labels[report.status] || report.status));
        card.append(heading);
        card.append(node("p", "", `Reference: ${report.id}`));
        card.append(node("p", "", `Category: ${report.category}`));
        card.append(node("p", "", `Location: ${report.area || report.landmark || "Not provided"}`));
        card.append(node("p", "", `Submitted: ${dateText(report.created_at)}`));
        if (report.latest_update) card.append(node("p", "", `Latest update: ${report.latest_update}`));
        const open = node("button", "button button--secondary", "View timeline");
        open.type = "button";
        open.addEventListener("click", () => {
          input.value = report.id;
          form.requestSubmit();
        });
        card.append(open);
        myReportList.append(card);
      });
    } catch (error) {
      myReportsState.textContent = error.message || "Your reports could not be loaded.";
    } finally {
      if (refreshMyReports) refreshMyReports.disabled = false;
    }
  }

  const params = new URLSearchParams(window.location.search);
  const reportIdParam = params.get("reportId");
  if (reportIdParam) input.value = reportIdParam;
  refreshMyReports?.addEventListener("click", loadMyReports);
  loadMyReports();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = input.value.trim();
    if (!id) {
      setState("Enter your report ID to check its status.", "error");
      input.focus();
      return;
    }

    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Looking up…";
    result.replaceChildren();
    setState("Looking up your report…", "loading");

    try {
      const data = await api.getTracking(id);
      render(data);
      setState("Report found. This is the latest status available from the API.", "success");
    } catch (error) {
      result.replaceChildren();
      setState(error.message || "Could not find this report. Check the ID and try again.", "error");
    } finally {
      submit.disabled = false;
      submit.textContent = "Track report";
    }
  });
})();
