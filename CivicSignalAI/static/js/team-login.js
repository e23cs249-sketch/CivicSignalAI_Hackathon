const form = document.querySelector("#team-login-form");
const emailInput = document.querySelector("#team-email");
const passwordInput = document.querySelector("#team-password");
const toggle = document.querySelector(".field-toggle");
const message = document.querySelector("#team-login-message");
const submit = form?.querySelector('button[type="submit"]');

function showMessage(text, kind = "error") {
  message.textContent = text;
  message.classList.toggle("error-message", kind === "error");
  message.classList.toggle("success", kind === "success");
}

toggle?.addEventListener("click", () => {
  const visible = passwordInput.type === "password";
  passwordInput.type = visible ? "text" : "password";
  toggle.textContent = visible ? "Hide" : "Show";
  toggle.setAttribute("aria-label", visible ? "Hide password" : "Show password");
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  showMessage("");
  submit.disabled = true;
  submit.textContent = "Verifying access…";

  try {
    const response = await fetch("/api/auth/team/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email: emailInput.value, password: passwordInput.value }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Sign-in failed. Please try again.");

    showMessage("Access verified. Opening the team workspace…", "success");
    const next = new URLSearchParams(window.location.search).get("next");
    const destination = next && next.startsWith("/") && !next.startsWith("//") ? next : "/team";
    window.location.assign(destination);
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "Sign-in service is unavailable. Please try again.");
  } finally {
    submit.disabled = false;
    submit.textContent = "Sign in to workspace";
  }
});