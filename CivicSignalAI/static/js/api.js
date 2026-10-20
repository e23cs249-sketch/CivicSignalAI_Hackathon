export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function postJson(path, payload) {
  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ApiError(0, { detail: "The local service could not be reached." });
  }

  let body;
  try {
    body = await response.json();
  } catch {
    body = { detail: "The service returned an unreadable response." };
  }

  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body;
}
