# CivicSignal AI

**A civic issue reporting and tracking prototype connecting residents with authorized response teams.**

CivicSignal AI is a web application built with FastAPI, SQLite, and HTML, CSS, and JavaScript. Residents can submit civic issues with a confirmed location and optional photos, then track their own reports. Authorized staff can review the same reports, update statuses, and add progress notes or photos through a protected dashboard.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Run the Application](#run-the-application)
- [Citizen Sign-up and Login](#citizen-sign-up-and-login)
- [Staff Account Setup](#staff-account-setup)
- [Testing](#testing)
- [Security and Privacy](#security-and-privacy)
- [Current Limitations](#current-limitations)
- [Hackathon Submission](#hackathon-submission)

## Overview

Residents need a clear way to report local problems and follow their progress. CivicSignal AI provides a shared workflow for residents to submit reports and authorized staff to manage responses. Reports can include a description, address or confirmed map location, and supporting photos. A persisted timeline records status changes and updates.

The application also provides rule-based analysis and possible-duplicate suggestions before submission. These are heuristics, not externally generated AI results or verified facts.

### Intended Users

- **Residents:** Create accounts, report civic issues, and track their own submissions.
- **Authorized staff:** Review reports, update statuses, and document progress.
- **Evaluators and developers:** Explore a working prototype of a citizen-to-response workflow.

## Key Features

### Citizen Experience

- Citizen registration and login with protected reporting and tracking pages.
- Report title, category, description, area/address, and optional confirmed coordinates.
- Leaflet map location selection and optional browser location detection.
- Optional JPG, PNG, and WebP report photos.
- Rule-based analysis, missing-detail prompts, and possible-duplicate suggestions.
- Citizen-owned report listing, status, timeline, and authorized photo access.

### Staff Dashboard

- Protected staff login with password hashing and login throttling.
- Searchable and filterable report queue.
- Status updates, progress notes, rejection reasons, and progress-photo uploads.
- Interactive staff account provisioning from a local command-line utility.

### Data and Privacy

- SQLite persistence for reports, ownership, accounts, sessions, and timeline events.
- Private image storage outside the publicly served static directory.
- Server-side image validation and re-encoding, with access checks when images are retrieved.

## How It Works

1. A resident signs up or logs in.
2. They enter an issue and optionally choose and confirm a location or attach photos.
3. They review the report and optional rule-based suggestions, then submit it.
4. The application stores the report, owner, and initial timeline event in SQLite; photos are stored privately.
5. Authorized staff review the same report in the dashboard and may update its status, add a note, or upload progress photos.
6. The resident returns to tracking to see the current status, timeline, and permitted evidence.

## Technology Stack

| Component | Technology |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite via Python's standard-library `sqlite3` |
| Frontend | HTML, CSS, JavaScript |
| Map | Leaflet and OpenStreetMap tiles |
| Image handling | Pillow, `python-multipart` |
| Tests | Pytest |

## Project Structure

```text
CivicSignalAI/
├── app/                    # FastAPI routes, SQLite, auth, workflow, media, analysis
├── static/                 # Citizen pages, styles, and browser scripts
├── tests/                  # API, auth, media, persistence, and workflow tests
├── devpost/
│   ├── scope.md
│   ├── prd.md
│   ├── spec.md
│   ├── checklist.md
│   ├── app-map.html
│   └── submission-draft.md
├── team-login.html         # Staff sign-in page
├── team-signup.html        # Staff approval information, not account registration
├── team.html               # Staff dashboard
├── tracking.html           # Citizen report tracking
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

`App.tsx` and `index.css` are retained workspace files but are not part of the active FastAPI serving path. The workspace also contains Devpost Learn Skill Pack files; verify redistribution terms before publishing them.

## Prerequisites

- Python 3.11 or newer. This workspace's verified virtual environment uses Python 3.14.7.
- PowerShell on Windows or an equivalent terminal.
- A modern web browser.
- Node.js only for the documented JavaScript syntax checks.

## Installation

Open a terminal in the directory containing `app/`, `static/`, and `requirements.txt`. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, invoke the virtual environment's Python directly, for example `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Configuration

The app reads process environment variables; it does not automatically load a `.env` file. `.env.example` documents the supported settings:

| Variable | Purpose | Local default |
| --- | --- | --- |
| `CIVICSIGNAL_DATABASE_PATH` | SQLite database location | `./data/civicsignal.db` |
| `CIVICSIGNAL_COOKIE_SECURE` | Enables the Secure cookie flag for HTTPS | `false` |
| `CIVICSIGNAL_UPLOAD_DIR` | Private image storage location | `./data/private-uploads` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google OAuth client and exact callback URI | Unset; Google sign-in disabled |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI` | LinkedIn OAuth client and exact callback URI | Unset; LinkedIn sign-in disabled |
| `CIVICSIGNAL_OAUTH_STATE_SECRET` | At least 32 bytes used to sign short-lived OAuth state | Unset; provider sign-in disabled |

The defaults work for local development. For HTTPS, set `CIVICSIGNAL_COOKIE_SECURE=true` in the server environment. Keep uploads in persistent private storage outside the public static directory. Never put real secrets in `.env.example` or commit local environment files.

## Run the Application

From the project root, start the development server:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/` for citizen access. Other routes:

| Route | Purpose |
| --- | --- |
| `/` | Citizen sign-up and login |
| `/home` | Citizen home page after login |
| `/report` | Protected issue reporting flow |
| `/tracking.html` | Protected report tracking |
| `/team-login` | Staff login |
| `/team-signup` | Staff approval information only |
| `/team` | Protected staff dashboard |

Vercel serves this FastAPI application from the repository-root `index.py`, which imports `app.main:app`. The app resolves `static/` relative to `app/main.py` and mounts it at `/static`; keep the Vercel project root set to the folder containing `index.py`, `app/`, and `static/`. The deployed `/api/health` endpoint and static page routes were checked. No Vercel routing rewrite is needed for this existing deployment.

## Citizen Sign-up and Login

1. Open `http://127.0.0.1:8000/` and choose **Sign up**.
2. Enter a full name, phone number, and email address.
3. Set and confirm a password of at least 12 characters, accept the terms, and select **Create account**. Successful registration opens `/home`.
4. For later visits, choose **Log in**, enter the registered email and password, and submit. Successful login opens `/home`.

The citizen session is required to submit reports and view the account's reports. Password reset and Google/LinkedIn sign-in are not configured.

### Google and LinkedIn Sign-in

The authorization-code flows use PKCE, short-lived signed state cookies, server-side token exchange, and verified provider email. Tokens and provider identifiers are not sent to browser JavaScript or persisted. OAuth authenticates an existing active CivicSignal citizen account by its verified email; first create the account through the normal sign-up form using the same email address. A provider cannot create an account or bypass the existing terms acceptance flow. This does not alter the database schema.

To enable production sign-in, add these variables in **Vercel Project → Settings → Environment Variables**, selecting the Production environment (and Preview too if you want OAuth previews):

| Vercel variable | Value |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Client ID from a Google OAuth web application |
| `GOOGLE_CLIENT_SECRET` | Client secret from that same Google OAuth client |
| `GOOGLE_REDIRECT_URI` | `https://civic-signal-ai.vercel.app/api/auth/citizen/oauth/google/callback` |
| `LINKEDIN_CLIENT_ID` | Client ID from your LinkedIn app |
| `LINKEDIN_CLIENT_SECRET` | Client secret from that same LinkedIn app |
| `LINKEDIN_REDIRECT_URI` | `https://civic-signal-ai.vercel.app/api/auth/citizen/oauth/linkedin/callback` |
| `CIVICSIGNAL_OAUTH_STATE_SECRET` | A newly generated random secret of at least 32 bytes; do not reuse an OAuth client secret |

Generate the state secret locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and enter its output directly into Vercel. Do not commit it or paste it into source files.

In **Google Cloud Console**, configure the OAuth consent screen and create an OAuth Client ID of type **Web application**. Add `civic-signal-ai.vercel.app` as an authorized domain and register the exact Google callback URI above under **Authorized redirect URIs**. Request the OpenID Connect `openid`, `email`, and `profile` scopes, and add test users if the consent screen remains in testing mode.

In **LinkedIn Developer Portal**, enable the **Sign In with LinkedIn using OpenID Connect** product for the app, register the exact LinkedIn callback URI above under its authorized redirect URLs, and ensure the `openid`, `profile`, and `email` scopes are available.

The redirect URI in each Vercel variable must exactly match its provider-console entry, including scheme, host, path, and trailing-slash choice. Save the variables and redeploy. OAuth has not been tested against real providers because credentials and provider-console settings are not available in this workspace; until configured, the buttons return a visible setup message.

Vercel serverless filesystems are not durable storage. This project currently uses SQLite and local private-file storage; configure a persistent database and private upload store before relying on production account linking, report persistence, or media uploads. No data was migrated or deleted as part of this change.

## Staff Account Setup

There is no public staff registration endpoint and no default administrator account is seeded at startup. An authorized operator provisions an approved staff account interactively from the project root:

```powershell
python -m app.provision_team_user
```

The utility prompts for an approved staff work email, a password, and password confirmation. Password entry is hidden and should not be included in a command or shell history. Use the exact approved email and the private password chosen during provisioning at `http://127.0.0.1:8000/team-login`; a successful login opens `/team`.

The `/team-signup` page explains staff approval; it does not create an account. Provisioning does not reset or modify existing accounts.

## Judge Demo Login

These are intentionally public, disposable credentials for the isolated local judge-demo database only. They are not the main administrator's credentials and must never be used for production or a shared deployment.

| Credential | Demo value |
| --- | --- |
| Staff email | `judge-demo@civicsignal.local` |
| Staff password | `JudgeDemo-CivicSignal-2026!` |
| Staff login | `http://127.0.0.1:8000/team-login` |

### Run the existing judge-demo database

This workspace has the judge account in `data/judge-demo.db`, separate from the normal `data/civicsignal.db`. From the project root in PowerShell, start the isolated demo with the launcher:

```powershell
.\run-judge-demo.ps1
```

The launcher sets the demo database and upload paths each time, then starts the development server. It uses `.venv` when available, otherwise the Python launcher (`py -3`) or `python`. This does not change the database used by the normal app command. Then sign in at `http://127.0.0.1:8000/team-login` with the demo values above. The isolated database and upload directory are local-only and excluded from Git.

### Set up the judge account in a fresh clone

The ignored database is not included in a repository clone. To create the same disposable account locally, set the same isolated paths, run the interactive provisioner, and enter the published demo values when prompted. Then start the server with those paths still set:

```powershell
$env:CIVICSIGNAL_DATABASE_PATH = Join-Path (Get-Location) "data\judge-demo.db"
$env:CIVICSIGNAL_UPLOAD_DIR = Join-Path (Get-Location) "data\private-uploads\judge-demo"
python -m app.provision_team_user
.\run-judge-demo.ps1
```

This public demo login is intended only for a local disposable database. Do not put personal or production administrator credentials in this README, screenshots, or demo video. Keep judge testing data synthetic.

## Testing

Run the backend suite from the project root:

```powershell
python -m pytest -q
```

Run the JavaScript syntax checks (Node.js required):

```powershell
node --check static/js/auth.js
node --check static/js/citizen-session.js
node --check static/js/api-client.js
node --check static/js/tracking.js
node --check static/js/team-dashboard.js
node --check --experimental-default-type=module static/js/app.js
```

The last recorded run completed with **46 passed tests and 12 passing subtests**; it emitted an existing Starlette/httpx `TestClient` deprecation warning. Rerun checks after code changes. No frontend build pipeline or automated browser end-to-end suite is configured.

## Security and Privacy

- Citizen report listing, tracking, uploads, and image access are restricted by report ownership. Staff-only workflows require an authenticated staff session.
- Passwords are stored as scrypt hashes. Session tokens are stored as hashes; cookies are HTTP-only and SameSite Strict. Configure the Secure cookie flag for HTTPS deployments.
- JPG, PNG, and WebP uploads are validated and re-encoded; the app limits uploads to four images per request and 5 MB per image. Images are served through an authorization-checked endpoint, not directly from `static/`.
- Treat report descriptions, email addresses, phone numbers, locations, coordinates, and photos as private. Use synthetic accounts, fictional reports, and non-sensitive images in demos.
- Exclude `.env`, databases, uploads, personal/production credentials, and learner-profile information from public repositories. The documented judge credentials are intentionally public and only usable with a locally provisioned, disposable demo database. Inspect selected files and available Git history before publication.
- The local database may contain existing accounts. Review accounts through an authorized process; do not expose account identifiers or credentials in repository documentation.

## Current Limitations

- Analysis and duplicate detection are rule-based heuristics, not external AI.
- The prototype is not connected to a live government or municipal service.
- SQLite and filesystem uploads are local, single-host storage; production use requires persistent private storage, backups, permissions, and operational controls.
- Map tiles, Google Fonts, and some visual assets require network access.
- Cloud storage/database, OAuth, password-reset email, SMS notifications, and external agency integrations are not configured.
- `requirements.txt` is not version-pinned and no Python dependency lockfile is configured, so installs are not fully reproducible.
- No automated frontend build or browser end-to-end test suite is configured.

## Hackathon Submission

CivicSignal AI is being prepared for [Build With AI: Basics](https://learn-ai-basics.devpost.com/). This README documents the app but does not establish hackathon eligibility or prove that a learner completed Skill Pack activities.

The challenge requires a new project started from an empty folder during the submission period, actual use of the Devpost Learn Skill Pack in a supported coding agent, and a public repository containing `devpost/scope.md`, `devpost/prd.md`, and `devpost/spec.md`. The workspace cannot verify the project start history or Skill Pack use; the owner must confirm these from genuine records. The planning files retain the original plan and include dated implementation notes.

Submit a **1–3 minute demo video** and a public GitHub, GitLab, or Bitbucket repository URL. Reviewers are not expected to clone and run the project, so the recording should clearly show the app working end-to-end. The project description must explain what it does, who it serves, and what the team learned; the team must write the learning reflection from genuine experience. The local storyboard and factual notes are in [`devpost/submission-draft.md`](devpost/submission-draft.md).

The judging criteria emphasize a coherent product experience (**Design**), a clear and useful idea (**Innovation/Idea**), and a presentation that demonstrates the flow and explains its problem and audience (**Presentation**). No video has been recorded or uploaded, and no public repository URL is verified in this workspace. Check the live challenge page for current deadlines and submission details.

For public repository preparation, include the active app source, static assets, tests, setup files, README, and the three required planning documents. Exclude local databases, private uploads, `.env`, virtual environments, caches, logs, learner-profile files, internal audit reports, personal/production credentials, and real user/report data. The documented judge credentials are intentionally public; the corresponding local database is ignored and must not be published. Keep `App.tsx` and `index.css` until their owner confirms their purpose. Verify Skill Pack redistribution terms before publishing skill files or lock metadata. No repository was initialized or published from this workspace.
