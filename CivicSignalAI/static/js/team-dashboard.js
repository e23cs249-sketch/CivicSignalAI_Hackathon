(function () {
  "use strict";
  const api = window.CivicSignalAPI;
  const list = document.querySelector("#report-list");
  const detail = document.querySelector("#report-detail");
  const state = document.querySelector("#dashboard-state");
  const refreshButton = document.querySelector("#refresh-reports");
  const filter = document.querySelector("#status-filter");
  const categoryFilter = document.querySelector("#category-filter");
  const dateFilter = document.querySelector("#submitted-after");
  const searchInput = document.querySelector("#report-search");
  const logoutButton = document.querySelector("#team-logout");
  if (!api || !list || !state) return;

  let reports = [];
  let selectedReportId = null;
  const labels = {
    submitted: "Submitted",
    acknowledged: "Under review",
    in_progress: "In progress",
    resolved: "Resolved",
    rejected: "Rejected",
  };

  function setState(message, kind = "info") {
    state.textContent = message;
    state.className = `notice notice--${kind}`;
    state.hidden = !message;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function formatDate(value) {
    if (!value) return "Date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  function summaryCounts() {
    const counts = { submitted: 0, acknowledged: 0, in_progress: 0, resolved: 0, rejected: 0 };
    reports.forEach((report) => {
      if (report.status === "submitted") counts.submitted += 1;
      if (report.status === "acknowledged") counts.acknowledged += 1;
      if (report.status === "in_progress") counts.in_progress += 1;
      if (report.status === "resolved") counts.resolved += 1;
      if (report.status === "rejected") counts.rejected += 1;
    });
    return counts;
  }

  function renderSummary() {
    const cards = {
      total: document.querySelector("#summary-total"),
      submitted: document.querySelector("#summary-submitted"),
      acknowledged: document.querySelector("#summary-review"),
      in_progress: document.querySelector("#summary-progress"),
      resolved: document.querySelector("#summary-resolved"),
      rejected: document.querySelector("#summary-rejected"),
    };
    const counts = summaryCounts();
    cards.total.textContent = String(reports.length);
    cards.submitted.textContent = String(counts.submitted);
    cards.acknowledged.textContent = String(counts.acknowledged);
    cards.in_progress.textContent = String(counts.in_progress);
    cards.resolved.textContent = String(counts.resolved);
    cards.rejected.textContent = String(counts.rejected);
  }

  function filteredReports() {
    const selectedStatus = filter ? filter.value : "all";
    const selectedCategory = categoryFilter ? categoryFilter.value : "all";
    const after = dateFilter?.value ? new Date(`${dateFilter.value}T00:00:00`).getTime() : null;
    const query = (searchInput?.value || "").trim().toLocaleLowerCase();
    return reports.filter((report) => {
      if (selectedStatus !== "all" && report.status !== selectedStatus) return false;
      const categoryMatches = report.category === selectedCategory
        || (selectedCategory === "damaged_road" && report.category === "potholes");
      if (selectedCategory !== "all" && !categoryMatches) return false;
      if (after != null && new Date(report.created_at).getTime() < after) return false;
      const searchable = [report.id, report.title, report.description, report.area, report.landmark]
        .filter(Boolean).join(" ").toLocaleLowerCase();
      return !query || searchable.includes(query);
    });
  }

  async function renderDetail(report) {
    if (!detail) return;
    detail.replaceChildren();
    if (!report) {
      selectedReportId = null;
      detail.append(element("p", "empty-state", "Select a report to review its timeline and update its status."));
      return;
    }
    selectedReportId = report.id;

    const heading = element("div", "detail-header");
    heading.append(element("h3", "", report.title || `Report ${report.id}`));
    heading.append(element("span", `status-badge status-badge--${report.status}`, labels[report.status] || report.status));
    detail.append(heading);
    detail.append(element("p", "report-card__meta", `Category: ${report.category || "Not provided"}`));
    if (report.area) detail.append(element("p", "report-card__meta", `Area: ${report.area}`));
    detail.append(element("p", "report-card__meta", `Location: ${report.landmark || "Not provided"}`));
    if (report.latitude != null && report.longitude != null) {
      const mapLink = element("a", "report-card__meta", `Map: ${Number(report.latitude).toFixed(6)}, ${Number(report.longitude).toFixed(6)}`);
      mapLink.href = `https://www.openstreetmap.org/?mlat=${encodeURIComponent(report.latitude)}&mlon=${encodeURIComponent(report.longitude)}#map=17/${encodeURIComponent(report.latitude)}/${encodeURIComponent(report.longitude)}`;
      mapLink.target = "_blank";
      mapLink.rel = "noopener noreferrer";
      detail.append(mapLink);
    }
    detail.append(element("p", "report-card__meta", `Submitted: ${formatDate(report.created_at)}`));
    detail.append(element("p", "report-card__description", report.description || "No description available."));

    const timelineSection = element("section", "detail-timeline");
    timelineSection.append(element("h4", "", "Status timeline"));
    const timeline = element("ol", "detail-timeline__list");
    timeline.append(element("li", "empty-state", "Loading report history…"));
    timelineSection.append(timeline);
    detail.append(timelineSection);

    const actions = element("form", "status-form");
    const statusWrap = element("label", "", "Update status");
    const select = element("select", "status-select");
    select.name = "status";
    const options = ["submitted", "acknowledged", "in_progress", "resolved", "rejected"];
    options.forEach((status) => {
      const option = element("option", "", labels[status]);
      option.value = status;
      option.selected = status === report.status;
      select.append(option);
    });
    statusWrap.append(select);

    const noteWrap = element("label", "", "Progress note or resolution/rejection reason");
    const messageInput = element("textarea", "");
    messageInput.name = "message";
    messageInput.rows = 3;
    messageInput.maxLength = 1000;
    messageInput.placeholder = "Describe review, work in progress, completion, or rejection reason";
    noteWrap.append(messageInput);

    const fileWrap = element("div", "admin-upload-field");
    const fileLabel = element("label", "", "Progress photos (optional, up to 4; 5 MB each)");
    const fileInput = element("input", "");
    fileInput.id = "progress-photos";
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.accept = "image/jpeg,image/png,image/webp";
    fileLabel.htmlFor = fileInput.id;
    fileWrap.append(fileLabel, fileInput);
    const photoPreview = element("div", "admin-photo-preview");
    let selectedFiles = [];
    function renderPhotoPreview() {
      photoPreview.querySelectorAll("img").forEach((image) => URL.revokeObjectURL(image.src));
      photoPreview.replaceChildren();
      selectedFiles.forEach((file, index) => {
        const card = element("div", "admin-photo-preview__item");
        const image = document.createElement("img");
        image.src = URL.createObjectURL(file);
        image.alt = `Selected progress photo: ${file.name}`;
        const remove = element("button", "button button--secondary", "Remove");
        remove.type = "button";
        remove.addEventListener("click", () => {
          selectedFiles.splice(index, 1);
          renderPhotoPreview();
        });
        card.append(image, remove);
        photoPreview.append(card);
      });
    }
    fileInput.addEventListener("change", () => {
      const addedFiles = [...fileInput.files];
      const invalid = addedFiles.find((file) => !["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024);
      if (selectedFiles.length + addedFiles.length > 4 || invalid) {
        feedback.textContent = selectedFiles.length + addedFiles.length > 4 ? "Choose no more than 4 photos." : "Use JPG, PNG, or WebP images no larger than 5 MB.";
        fileInput.value = "";
        return;
      }
      selectedFiles.push(...addedFiles);
      fileInput.value = "";
      renderPhotoPreview();
    });
    fileWrap.append(photoPreview);

    const button = element("button", "button button--primary", "Save update");
    button.type = "submit";
    const feedback = element("span", "form-feedback");
    feedback.setAttribute("aria-live", "polite");
    actions.append(statusWrap, noteWrap, fileWrap, button, feedback);

    actions.addEventListener("submit", async (event) => {
      event.preventDefault();
      const nextStatus = select.value;
      const message = messageInput.value.trim();
      if (nextStatus === "resolved" && report.status !== "resolved" && !message) {
        feedback.textContent = "A resolution note is required before resolving.";
        messageInput.focus();
        return;
      }
      if (nextStatus === "rejected" && report.status !== "rejected" && !message) {
        feedback.textContent = "A rejection reason is required.";
        messageInput.focus();
        return;
      }
      button.disabled = true;
      feedback.textContent = "Saving…";
      try {
        await api.updateReport(report.id, nextStatus, message, selectedFiles, (percent) => {
          feedback.textContent = `Uploading and saving: ${percent}%`;
        });
        const refreshed = await api.listReports();
        reports = refreshed;
        setState("Report update saved successfully.", "success");
        render();
        const updatedReport = reports.find((item) => item.id === report.id);
        if (updatedReport) await renderDetail(updatedReport);
      } catch (error) {
        if (error.status === 401) {
          window.location.replace("/team-login");
          return;
        }
        feedback.textContent = error.message || "Could not update the report.";
      } finally {
        button.disabled = false;
      }
    });

    detail.append(actions);

    try {
      const tracking = await api.getTracking(report.id);
      if (selectedReportId !== report.id) return;
      timeline.replaceChildren();
      if (!tracking.timeline.length) {
        timeline.append(element("li", "empty-state", "No status history is available."));
      } else {
        const mediaByEvent = new Map();
        tracking.images.forEach((image) => {
          if (!image.event_id || image.media_type === "original") return;
          const items = mediaByEvent.get(image.event_id) || [];
          items.push(image);
          mediaByEvent.set(image.event_id, items);
        });
        tracking.timeline.forEach((event) => {
          const status = event.status_to || event.event_type || "Update";
          const item = element("li", "detail-timeline__item");
          item.append(element("strong", "", labels[status] || status.replaceAll("_", " ")));
          item.append(element("time", "", formatDate(event.created_at)));
          if (event.message) item.append(element("p", "", event.message));
          if (event.actor_name) item.append(element("small", "", `Updated by ${event.actor_name}`));
          (mediaByEvent.get(event.id) || []).forEach((image) => {
            const photo = document.createElement("img");
            photo.className = "timeline-photo";
            photo.src = image.url;
            photo.alt = image.media_type === "original" ? "Original citizen report photo" : "Administrator progress photo";
            item.append(photo);
          });
          timeline.append(item);
        });
      }
      const originals = tracking.images.filter((image) => image.media_type === "original");
      if (originals.length) {
        const gallery = element("section", "admin-evidence");
        gallery.append(element("h4", "", "Original citizen photos"));
        originals.forEach((image) => {
          const photo = document.createElement("img");
          photo.src = image.url;
          photo.alt = "Original citizen report photo";
          gallery.append(photo);
        });
        detail.insertBefore(gallery, actions);
      }
    } catch (error) {
      if (error.status === 401) {
        window.location.replace("/team-login");
        return;
      }
      timeline.replaceChildren(element("li", "empty-state", error.message || "Could not load report history."));
    }
  }

  function render() {
    list.replaceChildren();
    const visible = filteredReports();

    renderSummary();

    if (!visible.length) {
      list.append(element("p", "empty-state", reports.length ? "No reports match these filters." : "There are no reports to display yet."));
      return;
    }

    visible.forEach((report) => {
      const card = element("article", "report-card");
      const heading = element("div", "report-card__heading");
      heading.append(element("h3", "report-card__title", report.title || `Report ${report.id}`));
      heading.append(element("span", `status-badge status-badge--${report.status}`, labels[report.status] || report.status));
      card.append(heading);
      card.append(element("p", "report-card__meta", `Category: ${report.category || "Not provided"}`));
      card.append(element("p", "report-card__meta", `Submitted: ${formatDate(report.created_at)}`));
      card.append(element("p", "report-card__meta", `Location: ${report.area || report.landmark || "Not provided"}`));
      card.append(element("p", "report-card__description", report.description || "No description available."));

      const viewButton = element("button", "button button--secondary", "Review");
      viewButton.type = "button";
      viewButton.addEventListener("click", () => { void renderDetail(report); });
      card.append(viewButton);
      list.append(card);
    });
  }

  async function loadReports() {
    refreshButton && (refreshButton.disabled = true);
    if (refreshButton) refreshButton.textContent = "Loading…";
    setState("Loading reports…", "loading");
    list.replaceChildren();
    try {
      reports = await api.listReports();
      setState(reports.length ? `${reports.length} report(s) loaded.` : "No reports have been submitted yet.", reports.length ? "success" : "info");
      render();
      const selectedReport = reports.find((report) => report.id === selectedReportId) || reports[0];
      if (selectedReport) await renderDetail(selectedReport);
      else renderDetail(null);
    } catch (error) {
      if (error.status === 401) {
        window.location.replace("/team-login");
        return;
      }
      setState(error.message || "Could not load reports.", "error");
      list.append(element("p", "empty-state", "Reports could not be loaded."));
    } finally {
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh reports";
      }
    }
  }

  refreshButton && refreshButton.addEventListener("click", loadReports);
  [filter, categoryFilter, dateFilter].forEach((control) => control && control.addEventListener("change", render));
  searchInput && searchInput.addEventListener("input", render);
  logoutButton && logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Signing out…";
    try {
      await api.logout();
      window.location.replace("/team-login");
    } catch (error) {
      if (error.status === 401) {
        window.location.replace("/team-login");
        return;
      }
      setState(error.message || "Could not sign out. Please retry.", "error");
      logoutButton.disabled = false;
      logoutButton.textContent = "Sign out";
    }
  });
  loadReports();
})();
