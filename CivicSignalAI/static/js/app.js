import { ApiError, postJson } from "/static/js/api.js";

const form = document.querySelector("#report-form");
const description = document.querySelector("#description");
const title = document.querySelector("#report-title");
const category = document.querySelector("#category");
const area = document.querySelector("#area");
const landmark = document.querySelector("#landmark");
const previewButton = document.querySelector("#preview-button");
const submitButton = document.querySelector("#submit-button");
const formMessage = document.querySelector("#form-message");
const analysisPanel = document.querySelector("#analysis-panel");
const createdPanel = document.querySelector("#created-panel");
const descriptionCount = document.querySelector("#description-count");
const geoButton = document.querySelector("#geo-button");
const locationStatus = document.querySelector("#location-status");
const navToggle = document.querySelector(".nav-toggle");
const mobileNav = document.querySelector(".mobile-nav");
const issueCards = [...document.querySelectorAll(".issue-card")];
const reportTrigger = document.querySelector(".report-trigger");
const reportSection = document.querySelector("#report-section");
const latitudeInput = document.querySelector("#latitude");
const longitudeInput = document.querySelector("#longitude");
const locationConfirmed = document.querySelector("#location-confirmed");
const locationConfirmWrap = document.querySelector("#location-confirm-wrap");
const coordinateDisplay = document.querySelector("#coordinate-display");
const clearLocationButton = document.querySelector("#clear-location");
const mapElement = document.querySelector("#report-map");
const imageInput = document.querySelector("#report-images");
const imagePreviews = document.querySelector("#image-previews");
const uploadStatus = document.querySelector("#upload-status");
const reportSteps = [...document.querySelectorAll("[data-report-step]")];
const stepIndicators = [...document.querySelectorAll("[data-step-indicator]")];
const issueNextButton = document.querySelector("#issue-next-button");
const locationBackButton = document.querySelector("#location-back-button");
const reviewNextButton = document.querySelector("#review-next-button");
const reviewBackButton = document.querySelector("#review-back-button");
const reviewPanel = document.querySelector("#report-review");

let previewSignature = null;
let previewState = "idle";
let selectedImages = [];
let reportMap = null;
let reportMarker = null;
let currentStep = 1;

function validCoordinatePair(latitude, longitude) {
  return Number.isFinite(latitude)
    && Number.isFinite(longitude)
    && latitude >= -90
    && latitude <= 90
    && longitude >= -180
    && longitude <= 180;
}

function currentPayload() {
  const latitude = latitudeInput.value ? Number(latitudeInput.value) : null;
  const longitude = longitudeInput.value ? Number(longitudeInput.value) : null;
  const coordinatesValid = latitude !== null
    && longitude !== null
    && validCoordinatePair(latitude, longitude);
  const payload = {
    title: title.value.trim(),
    description: description.value,
    category: category.value,
    area: area.value.trim() || null,
    latitude: coordinatesValid ? latitude : null,
    longitude: coordinatesValid ? longitude : null,
    location_confirmed: coordinatesValid && locationConfirmed.checked,
  };
  if (landmark.value.trim()) {
    payload.landmark = landmark.value.trim();
  }
  return payload;
}

function signatureFor(payload) {
  return JSON.stringify({
    title: (payload.title || "").trim(),
    description: (payload.description || "").trim(),
    category: payload.category,
    area: (payload.area || "").trim() || null,
    landmark: (payload.landmark || "").trim() || null,
    latitude: payload.latitude,
    longitude: payload.longitude,
    location_confirmed: payload.location_confirmed,
  });
}

function updateCategoryCards() {
  const selected = category.value;
  issueCards.forEach((card) => {
    const active = card.dataset.category === selected;
    card.classList.toggle("is-selected", active);
    card.setAttribute("aria-pressed", String(active));
  });
}

function updateControls() {
  const latitude = latitudeInput.value ? Number(latitudeInput.value) : null;
  const longitude = longitudeInput.value ? Number(longitudeInput.value) : null;
  locationConfirmed.required = latitude !== null
    && longitude !== null
    && validCoordinatePair(latitude, longitude);
  const valid = form.checkValidity();
  previewButton.disabled = !valid || previewButton.dataset.busy === "true";
  submitButton.disabled = !valid || currentStep !== 3 || submitButton.dataset.busy === "true";
}

function setReportStep(step) {
  currentStep = step;
  reportSteps.forEach((panel) => {
    panel.hidden = Number(panel.dataset.reportStep) !== step;
  });
  stepIndicators.forEach((indicator) => {
    const active = Number(indicator.dataset.stepIndicator) === step;
    indicator.classList.toggle("is-active", active);
    indicator.classList.toggle("is-complete", Number(indicator.dataset.stepIndicator) < step);
  });
  updateControls();
  if (step === 2) {
    initializeMap();
    if (reportMap) setTimeout(() => reportMap.invalidateSize(), 0);
  }
  if (step === 3) renderReportReview();
}

function renderReportReview() {
  if (!reviewPanel) return;
  reviewPanel.replaceChildren();
  addText(reviewPanel, "h2", "Review your report");
  addText(reviewPanel, "h3", title.value.trim());
  addText(reviewPanel, "p", `Category: ${category.options[category.selectedIndex]?.text || category.value}`);
  addText(reviewPanel, "p", description.value.trim(), "report-review__description");
  if (area.value.trim()) addText(reviewPanel, "p", `Area: ${area.value.trim()}`);
  if (landmark.value.trim()) addText(reviewPanel, "p", `Address or landmark: ${landmark.value.trim()}`);
  if (latitudeInput.value && longitudeInput.value) {
    addText(reviewPanel, "p", `Confirmed coordinates: ${latitudeInput.value}, ${longitudeInput.value}`);
  }
  if (selectedImages.length) {
    addText(reviewPanel, "h3", "Selected report photos");
    const gallery = document.createElement("div");
    gallery.className = "image-previews";
    selectedImages.forEach((file) => {
      const figure = document.createElement("figure");
      figure.className = "report-review__photo";
      const image = document.createElement("img");
      image.src = URL.createObjectURL(file);
      image.alt = file.name;
      addText(figure, "figcaption", file.name);
      figure.prepend(image);
      gallery.append(figure);
    });
    reviewPanel.append(gallery);
  }
  if (!previewSignature || previewSignature !== signatureFor(currentPayload())) {
    addText(reviewPanel, "p", "Analysis preview is optional. You can submit this report as shown.", "report-review__note");
  }
}

function setFormMessage(message, klass = "") {
  formMessage.textContent = message;
  formMessage.className = `form-message ${klass}`.trim();
}

function addText(parent, tag, text, className = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function validationMessage(error) {
  const errors = error.body?.errors;
  if (Array.isArray(errors) && errors.length) {
    return errors.map((item) => `${item.field}: ${item.message}`).join(" ");
  }
  return error.message || "Something went wrong. Please try again.";
}

function renderAnalysis(result) {
  document.querySelector("#analysis-source").textContent = "Rule-based analysis";
  document.querySelector("#analysis-summary").textContent = result.summary || "No summary suggestion is available.";
  document.querySelector("#analysis-category").textContent = result.category_suggestion || "No category suggestion";
  document.querySelector("#analysis-priority").textContent = result.priority_hint || "No priority hint";

  const missingList = document.querySelector("#missing-fields");
  missingList.replaceChildren();
  if (result.missing_fields.length) {
    for (const item of result.missing_fields) addText(missingList, "li", item);
  } else {
    addText(missingList, "li", "No additional detail prompt.");
  }

  const duplicateList = document.querySelector("#duplicate-suggestions");
  duplicateList.replaceChildren();
  if (result.duplicate_suggestions.length) {
    for (const item of result.duplicate_suggestions) {
      addText(duplicateList, "li", `${item.summary} (${item.match_reason})`);
    }
  } else {
    addText(duplicateList, "li", "No possible duplicates found.");
  }
  analysisPanel.hidden = false;
}

function renderValidation(error) {
  setFormMessage(validationMessage(error));
}

function updateDescriptionCount() {
  descriptionCount.textContent = `${description.value.length} / 2000`;
}

function setLocationStatus(message, isError = false) {
  if (!locationStatus) return;
  locationStatus.textContent = message;
  locationStatus.classList.toggle("location-status--error", isError);
}

function setCoordinates(latitude, longitude, requiresConfirmation = true) {
  if (!validCoordinatePair(latitude, longitude)) {
    setLocationStatus("The selected location is invalid. You can continue without map coordinates.", true);
    return;
  }
  latitudeInput.value = latitude.toFixed(6);
  longitudeInput.value = longitude.toFixed(6);
  coordinateDisplay.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
  locationConfirmWrap.hidden = false;
  locationConfirmed.checked = !requiresConfirmation;
  locationConfirmed.required = true;
  if (reportMap) {
    const point = [latitude, longitude];
    if (!reportMarker) {
      reportMarker = L.marker(point, { draggable: true }).addTo(reportMap);
      reportMarker.on("dragend", () => {
        const moved = reportMarker.getLatLng();
        setCoordinates(moved.lat, moved.lng, true);
      });
    } else {
      reportMarker.setLatLng(point);
    }
    reportMap.setView(point, Math.max(reportMap.getZoom(), 16));
  }
  updateControls();
}

function initializeMap() {
  if (reportMap || !window.L || !mapElement) return;
  reportMap = L.map(mapElement).setView([20, 0], 2);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(reportMap);
  reportMap.on("click", (event) => {
    setCoordinates(event.latlng.lat, event.latlng.lng, true);
    setLocationStatus("Map location selected. Confirm the marker before submitting.");
  });
}

async function useCurrentLocation() {
  if (!navigator.geolocation) {
    setLocationStatus("This browser does not support location access.", true);
    return;
  }

  geoButton.disabled = true;
  geoButton.textContent = "Locating…";
  setLocationStatus("Your location is used only to place this issue marker. Allow access to continue.");

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 60000,
      });
    });

    initializeMap();
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;
    setCoordinates(latitude, longitude, true);
    setLocationStatus(`Location detected: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}. Confirm the marker to submit.`);
    form.dispatchEvent(new Event("input", { bubbles: true }));
  } catch (error) {
    const detail = error && error.code === error.PERMISSION_DENIED ? "Location permission was denied." : "Unable to access your current location.";
    setLocationStatus(detail, true);
  } finally {
    geoButton.disabled = false;
    geoButton.textContent = "Detect My Location";
  }
}

if (geoButton) {
  geoButton.addEventListener("click", useCurrentLocation);
}

issueNextButton?.addEventListener("click", () => {
  if (!title.reportValidity() || !category.reportValidity() || !description.reportValidity()) return;
  setFormMessage("");
  setReportStep(2);
  reportSection.scrollIntoView({ behavior: "smooth", block: "start" });
});

locationBackButton?.addEventListener("click", () => setReportStep(1));
reviewBackButton?.addEventListener("click", () => setReportStep(2));
reviewNextButton?.addEventListener("click", () => {
  if (!form.reportValidity()) return;
  setFormMessage("");
  setReportStep(3);
  reportSection.scrollIntoView({ behavior: "smooth", block: "start" });
});

if (reportTrigger && reportSection) {
  reportTrigger.addEventListener("click", () => {
    reportSection.hidden = false;
    initializeMap();
    if (reportMap) setTimeout(() => reportMap.invalidateSize(), 0);
    reportSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

document.querySelectorAll('a[href="#report-section"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    if (!reportSection) return;
    reportSection.hidden = false;
    initializeMap();
    if (reportMap) setTimeout(() => reportMap.invalidateSize(), 0);
    history.replaceState(null, "", "#report-section");
    reportSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

if (window.location.hash === "#report-section" && reportSection) {
  reportSection.hidden = false;
  initializeMap();
  if (reportMap) setTimeout(() => reportMap.invalidateSize(), 0);
}

if (reportSection && !reportSection.hidden) {
  initializeMap();
  if (reportMap) setTimeout(() => reportMap.invalidateSize(), 0);
}

if (navToggle && mobileNav) {
  navToggle.addEventListener("click", () => {
    const open = mobileNav.hidden;
    mobileNav.hidden = !open;
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  });
  mobileNav.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      mobileNav.hidden = true;
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Open navigation");
    }
  });
}

locationConfirmed.addEventListener("change", updateControls);

function renderImagePreviews() {
  imagePreviews.querySelectorAll("img").forEach((image) => URL.revokeObjectURL(image.src));
  imagePreviews.replaceChildren();
  selectedImages.forEach((file, index) => {
    const card = document.createElement("div");
    card.className = "image-preview";
    const image = document.createElement("img");
    image.alt = file.name;
    image.src = URL.createObjectURL(file);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${file.name}`);
    remove.addEventListener("click", () => {
      selectedImages.splice(index, 1);
      renderImagePreviews();
    });
    card.append(image, remove);
    imagePreviews.append(card);
  });
}

imageInput.addEventListener("change", () => {
  const files = [...imageInput.files];
  const validTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
  const invalid = files.find((file) => !validTypes.has(file.type) || file.size > 5 * 1024 * 1024);
  if (files.length > 4) {
    uploadStatus.textContent = "Choose no more than 4 photos.";
    uploadStatus.classList.add("location-status--error");
    imageInput.value = "";
    return;
  }
  if (invalid) {
    uploadStatus.textContent = `${invalid.name}: choose a JPG, PNG, or WebP image no larger than 5 MB.`;
    uploadStatus.classList.add("location-status--error");
    imageInput.value = "";
    return;
  }
  selectedImages = files;
  uploadStatus.textContent = files.length ? `${files.length} photo(s) ready to upload.` : "";
  uploadStatus.classList.remove("location-status--error");
  renderImagePreviews();
});

clearLocationButton.addEventListener("click", () => {
  latitudeInput.value = "";
  longitudeInput.value = "";
  locationConfirmed.checked = false;
  locationConfirmed.required = false;
  locationConfirmWrap.hidden = true;
  coordinateDisplay.textContent = "No coordinates selected";
  if (reportMarker && reportMap) {
    reportMap.removeLayer(reportMarker);
    reportMarker = null;
  }
  setLocationStatus("Manual address will be used without GPS coordinates.");
  updateControls();
});

function uploadImages(reportId, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/api/reports/${encodeURIComponent(reportId)}/images`);
    request.withCredentials = true;
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      let response;
      try { response = JSON.parse(request.responseText); } catch { response = {}; }
      if (request.status >= 200 && request.status < 300) resolve(response);
      else reject(new Error(response.detail || "Photos could not be uploaded."));
    });
    request.addEventListener("error", () => reject(new Error("Could not reach the server to upload photos.")));
    const data = new FormData();
    selectedImages.forEach((file) => data.append("files", file, file.name));
    request.send(data);
  });
}

issueCards.forEach((card) => {
  card.addEventListener("click", () => {
    category.value = card.dataset.category || "";
    updateCategoryCards();
    category.dispatchEvent(new Event("change"));
  });
});

form.addEventListener("input", () => {
  const signature = signatureFor(currentPayload());
  if (previewSignature !== signature) {
    previewSignature = null;
    previewState = "idle";
    analysisPanel.hidden = true;
    createdPanel.hidden = true;
    setFormMessage("Update the preview after changing report details.");
  }
  createdPanel.hidden = true;
  updateDescriptionCount();
  updateCategoryCards();
  updateControls();
});

form.addEventListener("change", () => {
  const signature = signatureFor(currentPayload());
  if (previewSignature !== signature) {
    previewSignature = null;
    previewState = "idle";
    analysisPanel.hidden = true;
    createdPanel.hidden = true;
    setFormMessage("Update the preview after changing report details.");
  }
  updateCategoryCards();
  updateControls();
});

previewButton.addEventListener("click", async () => {
  if (!form.reportValidity()) return;
  const payload = currentPayload();
  previewButton.dataset.busy = "true";
  previewButton.textContent = "Analyzing…";
  setFormMessage("");
  createdPanel.hidden = true;
  updateControls();

  try {
    const result = await postJson("/api/reports/preview", payload);
    renderAnalysis(result);
    previewSignature = signatureFor(payload);
    previewState = "success";
  } catch (error) {
    analysisPanel.hidden = true;
    if (error instanceof ApiError && error.status === 503) {
      previewSignature = signatureFor(payload);
      previewState = "unavailable";
      setFormMessage("Analysis unavailable; you may still submit your report.");
    } else {
      previewSignature = null;
      previewState = "idle";
      renderValidation(error);
    }
  } finally {
    previewButton.dataset.busy = "false";
    previewButton.textContent = "Preview analysis";
    updateControls();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity() || currentStep !== 3) return;
  const payload = currentPayload();
  submitButton.dataset.busy = "true";
  submitButton.textContent = "Submitting…";
  setFormMessage("");
  updateControls();

  try {
    const report = await postJson("/api/reports", payload);
    let photosSaved = false;
    let photoError = "";
    if (selectedImages.length) {
      uploadStatus.textContent = "Uploading photos: 0%";
      try {
        await uploadImages(report.id, (percent) => {
          uploadStatus.textContent = `Uploading photos: ${percent}%`;
        });
        photosSaved = true;
        uploadStatus.textContent = "Photos uploaded securely.";
      } catch (error) {
        photoError = error.message || "Photos could not be uploaded.";
        uploadStatus.textContent = photoError;
        uploadStatus.classList.add("location-status--error");
      }
    }
    analysisPanel.hidden = true;
    createdPanel.replaceChildren();
    createdPanel.className = "created-panel";
    addText(createdPanel, "h2", "Report submitted");
    addText(createdPanel, "p", `Report ID: ${report.id}`);
    if (photoError) {
      addText(createdPanel, "p", `Your report was saved, but its photos were not: ${photoError}`);
      const retryUpload = document.createElement("button");
      retryUpload.className = "button button-secondary";
      retryUpload.type = "button";
      retryUpload.textContent = "Retry photo upload";
      retryUpload.addEventListener("click", async () => {
        retryUpload.disabled = true;
        uploadStatus.textContent = "Uploading photos: 0%";
        try {
          await uploadImages(report.id, (percent) => {
            uploadStatus.textContent = `Uploading photos: ${percent}%`;
          });
          uploadStatus.textContent = "Photos uploaded securely.";
          selectedImages = [];
          renderImagePreviews();
          retryUpload.remove();
        } catch (error) {
          uploadStatus.textContent = error.message || "Photos could not be uploaded.";
          retryUpload.disabled = false;
        }
      });
      createdPanel.append(retryUpload);
    }
    const link = document.createElement("a");
    link.href = `/tracking.html?reportId=${encodeURIComponent(report.id)}`;
    link.textContent = "Track This Report";
    createdPanel.append(link);
    if (report.analysis_source === "unavailable") {
      createdPanel.classList.add("warning");
      addText(createdPanel, "p", report.analysis_warning || "Analysis unavailable; your report was saved without suggestions.");
    } else {
      addText(createdPanel, "p", "Your report is saved and ready for team review.");
    }
    createdPanel.hidden = false;
    form.reset();
    setReportStep(1);
    category.value = "";
    if (!selectedImages.length || photosSaved) {
      selectedImages = [];
      renderImagePreviews();
    }
    latitudeInput.value = "";
    longitudeInput.value = "";
    locationConfirmWrap.hidden = true;
    locationConfirmed.required = false;
    coordinateDisplay.textContent = "No coordinates selected";
    if (reportMarker && reportMap) {
      reportMap.removeLayer(reportMarker);
      reportMarker = null;
    }
    updateCategoryCards();
    previewSignature = null;
    previewState = "idle";
    updateDescriptionCount();
    setFormMessage("");
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      renderValidation(error);
    } else {
      createdPanel.replaceChildren();
      createdPanel.className = "created-panel error";
      addText(createdPanel, "p", error.message || "The report could not be saved. Please try again.");
      createdPanel.hidden = false;
    }
  } finally {
    submitButton.dataset.busy = "false";
    submitButton.textContent = "Submit report";
    updateControls();
  }
});

updateDescriptionCount();
updateCategoryCards();
updateControls();
