# CivicSignal AI

CivicSignal AI is a civic issue reporting and tracking prototype connecting residents with authorized response teams. Residents can register, report local issues with descriptions, locations, and optional photos, then track progress. Authorized administrators can review reports and post status updates through a protected dashboard.

## Features

- Citizen registration and sign-in with protected report submission and tracking.
- Civic reports with categories, locations, optional coordinates, and photos.
- Rule-based report summaries and possible duplicate suggestions.
- A private report dashboard for status changes, progress notes, and evidence.
- A private, owner-configured administrator login. Admin credentials and signed sessions do not use the application database.
- Optional Google and LinkedIn OAuth sign-in for existing citizen accounts.

## Technology and project structure

- Python, FastAPI, and Uvicorn serve the application and API.
- HTML, CSS, and JavaScript provide the browser interface.
- SQLite is the local database; PostgreSQL via `DATABASE_URL` is supported for deployed persistence.
- Pillow and `python-multipart` validate and store images.
- Pytest runs the backend tests.

```text
CivicSignalAI/
├── app/
│   ├── api/                 # Citizen/admin auth, reports, team and health routes
│   ├── services/            # Authentication helpers, analysis, workflow and media
│   ├── config.py            # Database configuration
│   ├── database.py          # SQLite/PostgreSQL persistence for app data
│   ├── migrate_sqlite_to_postgres.py # Optional citizen/report data migration
│   └── main.py              # FastAPI app, page routes and access guards
├── data/                    # Local databases and private uploads (not committed)
├── static/                  # Citizen pages, stylesheets and browser scripts
├── tests/                   # API, auth, persistence, media and workflow tests
├── index.py                 # Vercel FastAPI entry point
├── team-login.html          # Admin sign-in page
├── team-signup.html         # Admin configuration information; no public signup
├── team.html                # Protected admin dashboard
├── requirements.txt
└── README.md
```

## Requirements and local setup

Use Python 3.11 or newer. In PowerShell, open the project directory (the folder containing `app/`, `static/`, and `requirements.txt`) and run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Set administrator credentials in the server process environment; they are not stored in the database, source code, or browser code. The password and session-signing key below are entered/generated without putting their values in shell history:

```powershell
$env:ADMIN_USERNAME = Read-Host "Admin username"
$securePassword = Read-Host "Admin password" -AsSecureString
$env:ADMIN_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
$env:ADMIN_SESSION_SECRET = py -3 -c "import secrets; print(secrets.token_urlsafe(48))"
$env:DATABASE_URL = ""
$env:CIVICSIGNAL_DATABASE_PATH = Join-Path (Get-Location) "data\civicsignal.db"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Keep those variables set while the server runs. When finished, stop the server and clear the credentials:

```powershell
Remove-Item Env:ADMIN_USERNAME, Env:ADMIN_PASSWORD, Env:ADMIN_SESSION_SECRET
Remove-Item Env:DATABASE_URL, Env:CIVICSIGNAL_DATABASE_PATH
Remove-Variable securePassword
```

Open `http://127.0.0.1:8000/` for citizen sign-in or `http://127.0.0.1:8000/team-login` for administrator sign-in. The server does not automatically load `.env` files. `.env.example` lists supported variables but contains no actual secrets.

### Administrator authentication

Set these server-side environment variables:

| Variable | Required value |
| --- | --- |
| `ADMIN_USERNAME` | The exact administrator username chosen by the application owner |
| `ADMIN_PASSWORD` | The corresponding administrator password |
| `ADMIN_SESSION_SECRET` | A random secret of at least 32 bytes, used to sign the administrator session cookie |

Documentation-only example values:

```text
Admin username: civic_admin
Admin password: Civic@Admin#2026!X7
```

These are examples only; they are not automatically configured credentials or defaults. The admin login will accept them only if the project owner explicitly sets the exact matching `ADMIN_USERNAME` and `ADMIN_PASSWORD` values in **Vercel → Project Settings → Environment Variables → Production**, then redeploys. Do not use these example credentials for a real deployment; choose a unique, strong password instead.

Generate `ADMIN_SESSION_SECRET` as a random secret of at least 32 bytes. In PowerShell, for example: `py -c "import secrets; print(secrets.token_urlsafe(48))"`. Store it only as the server-side Vercel environment variable. For Production, `DATABASE_URL` must contain the connection URL for the project's production PostgreSQL database; it is required for citizen accounts and reporting, not admin authentication.

There are no built-in credentials. If any setting is missing or the session secret is too short, the admin login fails closed and reports that it is not configured. Do not use a `NEXT_PUBLIC_`, `VITE_`, or other client-exposed variable, and never place credentials in application source code or logs.

The server compares the supplied username and password against the configured values. On success it sets an expiring, signed, `HttpOnly`, `SameSite=Strict` cookie, marked `Secure` on HTTPS/Vercel. Admin login, session checks, and logout do not read or write the database. Direct requests to `/team`, `/team.html`, and admin APIs are checked on the server. Logout clears the browser cookie. Because sessions are stateless, an already copied cookie remains valid until its eight-hour expiry; changing `ADMIN_SESSION_SECRET` invalidates existing cookies.

Citizen account authentication and application data are separate: they continue to use the configured application database. On Vercel, `DATABASE_URL` is still required for citizen accounts, reports, sessions, and workflows; it is **not** used for administrator authentication. The optional `app.migrate_sqlite_to_postgres` utility migrates citizen and report data only. It does not migrate admin credentials or sessions.

## Configuration

The app reads process environment variables and does not automatically load `.env`. Variables relevant to local or deployed operation:

| Variable | Purpose |
| --- | --- |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET` | Required for admin sign-in; server-only secrets |
| `DATABASE_URL` | PostgreSQL connection URL for persistent deployed citizen/report data; optional locally |
| `CIVICSIGNAL_DATABASE_PATH` | SQLite path when `DATABASE_URL` is unset |
| `CIVICSIGNAL_COOKIE_SECURE` | Forces cookies Secure when `true`; the admin session cookie is always Secure on HTTPS/Vercel, even if this is `false` |
| `CIVICSIGNAL_UPLOAD_DIR` | Directory for private uploads; local filesystem by default |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Optional Google OAuth for existing citizen accounts |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI` | Optional LinkedIn OAuth for existing citizen accounts |
| `CIVICSIGNAL_OAUTH_STATE_SECRET` | Optional OAuth state-signing secret, at least 32 bytes |

OAuth provider settings are optional and unrelated to admin login. OAuth authenticates existing citizen accounts; it does not create public administrator accounts.

## Deploy to Vercel

This repository already exposes the FastAPI application through `index.py`; the frontend calls same-origin routes and needs no separate API URL or rewrite. Set the Vercel project **Root Directory** to `CivicSignalAI` (the directory containing `index.py`, `app/`, and `static/`) and use `main` as the Production Branch.

In **Vercel → Project → Settings → Environment Variables**, set the following for **Production** (also set them for Preview if needed):

- `ADMIN_USERNAME`: your chosen administrator username.
- `ADMIN_PASSWORD`: your chosen administrator password.
- `ADMIN_SESSION_SECRET`: a random secret of at least 32 bytes.
- `DATABASE_URL`: a PostgreSQL connection URL for persistent citizen and report data.

Use a hosted PostgreSQL provider such as Neon if needed. Configure the database separately; do not put its connection string in frontend code. In Vercel Production, leave `CIVICSIGNAL_COOKIE_SECURE` unset or set it to `true`; the admin session cookie is Secure on HTTPS/Vercel even if the variable is mistakenly set to `false`. The `.env.example` value `false` is for local plain-HTTP development only. Do not set `CIVICSIGNAL_DATABASE_PATH` on Vercel. Vercel's function filesystem is not durable, so local SQLite and local private upload files are not suitable for persistent production data.

#### Rate-limit administrator sign-in

The application does not use an in-memory or database counter for administrator login attempts. Before enabling public Production admin sign-in, configure a Vercel Firewall rate-limit rule, if available for the project plan:

- Match the exact path `/api/auth/team/login` and HTTP method `POST`.
- Rate-limit by source IP, using a conservative request limit and time window supported by the project’s Vercel plan; apply the rate-limit/block action.
- Do not include request bodies, passwords, or other credentials in rule logs.
- Check the Vercel Firewall events after enabling the rule and adjust it if legitimate staff sign-ins are blocked.

This rule is configured in Vercel, not by an application environment variable, and is not enabled by this repository. Confirm and enable it in the Vercel project before public Production use; no production configuration was changed as part of this code change. If Firewall rate limiting is unavailable for the project, do not treat this application alone as protected against repeated guesses—choose an approved shared rate-limit service or another deployment-level control before exposing admin sign-in.

If you need to retain existing SQLite citizen/report data, take a backup and review the optional `py -m app.migrate_sqlite_to_postgres --help` tool before using it with `DATABASE_URL` set. It is only for application data, not admin authentication. Existing legacy admin tables in a local database are not used by the app, are not deleted, and are not copied by this utility.

After adding environment variables, deploy the `main` Production branch or redeploy its latest commit so the new settings take effect. No application owner credentials or database connection values are included in this repository. This project does not currently provide a durable object-storage integration for uploaded photos; production photo persistence needs a private durable storage service or a host with persistent disk.

## Test the admin login and access controls

From the project directory:

```powershell
py -m pytest .\tests -q
node --check .\static\js\team-login.js
node --check .\static\js\team-dashboard.js
```

With the application running and the three `ADMIN_*` variables configured, verify:

1. The configured username and password sign in at `/team-login`.
2. A wrong password and an unknown username both show an error and do not establish a session.
3. `/team` and `/team.html` redirect to `/team-login` when signed out.
4. Admin APIs reject unauthenticated requests; after sign-in they accept the signed cookie.
5. `/api/auth/team/logout` clears the cookie and protected dashboard access is denied again.
6. Citizen sign-up, sign-in, reporting and report tracking remain available independently of admin credentials.

The tests exercise the login, invalid credentials, signed-cookie tampering, logout, direct-route access, and the fact that admin login/session checks do not connect to the database. A local test does not confirm Vercel production settings; test the deployed Production URL after configuring its environment variables.

## Limitations

- This is a prototype, not an integration with a municipal agency.
- Admin authentication uses one configured administrator account; there is no public or multi-user admin registration.
- Stateless sessions cannot be individually revoked server-side; they expire after eight hours, or immediately become invalid if `ADMIN_SESSION_SECRET` is changed.
- Citizen/report data on Vercel needs PostgreSQL. Vercel local files are ephemeral.
- Uploaded photos still use local filesystem storage and need separate durable private storage for production.
- OAuth login needs provider-side application setup and the corresponding environment variables.
- No automated browser end-to-end suite or separate frontend bundler/build pipeline is configured.
