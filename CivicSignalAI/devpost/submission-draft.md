# Devpost Description Draft and Demo Notes

Status: preparation notes, not a completed submission. The Learn Skill Pack Ship instructions require the learner to write the final public description and personal learning reflection. These verified facts are provided as a factual scaffold; no personal learning claim is supplied.

## Description facts to use

- **Project:** CivicSignal AI, a local prototype for civic issue reporting and response tracking.
- **Problem:** Residents may have difficulty submitting everyday public issues and following whether a response is underway.
- **Intended users:** Residents submitting reports and authorized municipal or community staff reviewing and updating them.
- **Implemented flow:** Citizen registration/sign-in; issue title/category/description; optional area/address; manually selected or browser-detected map coordinates with confirmation; optional private issue photo; report submission; citizen-owned tracking; authenticated staff queue, search/filter, status updates, progress notes/photos, and rejection reasons.
- **Analysis:** Rule-based summary/category/priority hints, missing-detail prompts, and possible duplicate suggestions. No external AI service is configured; suggestions are heuristic, not verified facts.
- **Useful distinction:** One persisted report and timeline connect a resident's tracking view with the staff workflow. Report ownership and private media access are enforced by the backend.
- **Limitations:** Local SQLite and filesystem media storage; external network resources for map tiles and some page assets; no live city integration, cloud storage/database, OAuth, password recovery, email/SMS delivery, or configured external AI.

## Team learning reflection

[Owner: replace this with the team's genuine learning reflection based on activities that actually occurred. This workspace does not establish who completed the Learn Skill Pack activities or what individuals learned.]

## Demo storyboard (target: about 2 minutes)

Use a disposable database and upload directory outside the repository. Provision a synthetic staff account before recording and keep credentials, account-management screens, terminal history, local database files, and real citizen data off-screen. Register a synthetic citizen for the recording. Use an invented report and a non-sensitive test image; select a generic demo map location unrelated to any real resident's home. Do not reuse records or images from the existing local database/upload folder.

- **0:00–0:12 — Context:** Show the CivicSignal AI sign-in and explain that this is a local prototype, not a live city service.
- **0:12–0:28 — Citizen access:** Register/sign in with a disposable synthetic account, then open the report page.
- **0:28–0:58 — Create:** Enter an invented issue, select its category, add a fictional address, choose and confirm a generic map marker, attach a harmless test image, review, and submit.
- **0:58–1:15 — Track:** Show the generated reference and the report in the signed-in citizen's list with its initial status.
- **1:15–1:42 — Staff response:** Switch to the staff session without displaying credentials. Open the same report in the dashboard, add a short progress note and non-sensitive progress photo if available, then change status to In progress.
- **1:42–1:55 — Verify shared update:** Return to the citizen tracking view, refresh, and show the updated status and timeline.
- **1:55–2:00 — Close:** State the local-storage and network-resource limitations. End without showing account details or private report data.

Before recording, verify that the form, map resources, image upload, citizen tracking, staff update, and refresh all work in the isolated demo environment. Never show passwords, tokens, real addresses, live resident information, or browser autofill.

## Demo setup outline

From the project root in PowerShell, create temporary storage and provision the staff account interactively before starting a separate recording session:

```powershell
$demoRoot = Join-Path $env:TEMP "civicsignal-demo"
New-Item -ItemType Directory -Force $demoRoot | Out-Null
$env:CIVICSIGNAL_DATABASE_PATH = Join-Path $demoRoot "demo.db"
$env:CIVICSIGNAL_UPLOAD_DIR = Join-Path $demoRoot "private-uploads"
python -m app.provision_team_user
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep the staff sign-in secret off the recording; do not put it in a command or this file. Use a separate synthetic citizen account. Treat the temporary database and uploads as disposable demo data, and do not redirect these variables to the project's existing `data/` directory.

## Submission evidence still needed

- Owner confirmation, using genuine dated records, that the project began from an empty folder during the hackathon period.
- Owner confirmation of actual Learn Skill Pack use and any learner activities, from reliable session/workflow evidence.
- Learner-written final project description and genuine learning reflection.
- Public repository URL created and verified by the owner after secret/privacy review and confirmation of skill-file redistribution terms.
- Demo video recorded and uploaded with reviewer-accessible permissions.

No public URL, eligibility evidence, completed learner walkthrough, recorded video, or upload is verified by this workspace.

## Recommended public-repository allowlist

- Active application source: `app/**`, `static/**`, `team-login.html`, `team-signup.html`, `team.html`, and `tracking.html`.
- Setup and tests: `README.md`, `.gitignore`, `.env.example`, `requirements.txt`, and `tests/**`.
- Public-safe submission documents: `devpost/scope.md`, `devpost/prd.md`, `devpost/spec.md`, `devpost/checklist.md`, `devpost/app-map.html`, and this file.
- Keep `skills-lock.json`, `.agents/skills/**`, and `agent/skills/**` in the workspace. Publish skill material only after the owner verifies it is necessary and its redistribution terms permit inclusion.

Exclude `.env` and other local environment files, `data/**`, SQLite databases, private uploads, `devpost/learner-profile.md`, `.venv/`, `node_modules/`, caches, logs, temporary outputs, local-only audit/phase reports, credentials, tokens, and any real report/user material. Keep `App.tsx` and `index.css` locally until their owner confirms their purpose; do not remove them as part of public packaging. No Git repository was initialized and no files were staged or published.
