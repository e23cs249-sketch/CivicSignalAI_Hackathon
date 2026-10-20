const loginForm = document.querySelector('#citizen-login-form');
const signupForm = document.querySelector('#citizen-signup-form');
const tabButtons = [...document.querySelectorAll('.tab-button')];
const loginMessage = document.querySelector('#login-message');
const signupMessage = document.querySelector('#signup-message');
const oauthErrors = {
  not_configured: 'This sign-in provider is not configured yet. Please use email and password or contact the site administrator.',
  invalid_state: 'The sign-in session expired or could not be verified. Please try again.',
  cancelled: 'Provider sign-in was cancelled.',
  provider_error: 'The identity provider could not complete sign-in. Please try again.',
  unverified_email: 'The provider must return a verified email address to sign in.',
  account_required: 'Create a CivicSignal account with this email first, then continue with your provider.',
  sign_in_failed: 'Sign-in could not be completed. Please try again.',
};

function setMessage(element, text, kind = '') {
  if (!element) return;
  element.textContent = text;
  element.className = `form-message ${kind}`.trim();
}

function showTab(target) {
  const isLogin = target === 'login-tab';
  tabButtons.forEach((button) => {
    const active = button.dataset.target === target;
    button.classList.toggle('is-active', active);
  });
  loginForm.classList.toggle('is-active', isLogin);
  signupForm.classList.toggle('is-active', !isLogin);
}

tabButtons.forEach((button) => {
  button.addEventListener('click', () => showTab(button.dataset.target));
});

document.querySelectorAll('[data-oauth-provider]').forEach((button) => {
  button.addEventListener('click', () => {
    window.location.assign(`/api/auth/citizen/oauth/${button.dataset.oauthProvider}`);
  });
});

const oauthError = new URLSearchParams(window.location.search).get('oauth_error');
if (oauthError && oauthErrors[oauthError]) {
  setMessage(loginMessage, oauthErrors[oauthError], 'error');
  window.history.replaceState(null, '', window.location.pathname);
}

document.querySelectorAll('[data-password-toggle]').forEach((button) => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.textContent = visible ? 'Hide' : 'Show';
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.setAttribute('aria-pressed', String(visible));
  });
});

document.querySelector('.forgot-link')?.addEventListener('click', (event) => {
  event.preventDefault();
  setMessage(loginMessage, 'Password reset is not configured for this deployment. Contact your administrator.', 'error');
});

async function sendJson(url, payload, messageElement) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail || 'Something went wrong.';
    setMessage(messageElement, detail, 'error');
    throw new Error(detail);
  }

  setMessage(messageElement, 'Success. Redirecting to your citizen dashboard…', 'success');
  return body;
}

loginForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setMessage(loginMessage, '', '');
  if (!loginForm.reportValidity()) return;
  const payload = {
    email: document.querySelector('#login-email').value.trim(),
    password: document.querySelector('#login-password').value,
  };

  try {
    await sendJson('/api/auth/citizen/login', payload, loginMessage);
    window.location.href = '/home';
  } catch (error) {
    // message already set by the helper
  }
});

signupForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setMessage(signupMessage, '', '');
  if (!signupForm.reportValidity()) return;
  const payload = {
    full_name: document.querySelector('#signup-name').value.trim(),
    phone: document.querySelector('#signup-phone').value.trim(),
    email: document.querySelector('#signup-email').value.trim(),
    password: document.querySelector('#signup-password').value,
    confirm_password: document.querySelector('#signup-confirm').value,
    accepted_terms: document.querySelector('#signup-terms').checked,
  };

  if (payload.password !== payload.confirm_password) {
    setMessage(signupMessage, 'Passwords do not match.', 'error');
    return;
  }

  try {
    await sendJson('/api/auth/citizen/register', payload, signupMessage);
    window.location.href = '/home';
  } catch (error) {
    // message already set by the helper
  }
});
