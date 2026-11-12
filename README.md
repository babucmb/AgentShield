# AgentShield

AgentShield is a safety layer between AI purchase recommendations and payment execution. The MVP turns a natural-language request into structured intent, verifies a controlled demo catalogue item, evaluates deterministic policies, and binds human approval to an exact proposal fingerprint.

## Run the MVP

```powershell
C:/Users/MAHESH/anaconda3/python.exe -m uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000/docs` for the API. The React console can be started with `npm install` and `npm run dev` from `frontend/`.

For the PayPal Sandbox demo, copy `.env.example` to `.env`, create a Sandbox REST app in the PayPal Developer Dashboard, and set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. Set `OPENAI_API_KEY` to enable live structured intent extraction; without it, the safe deterministic fallback keeps the demo runnable. Start the backend and frontend in separate terminals. The server creates Orders v2 orders only after an AgentShield approval and calculates the amount from the server catalogue.

Demo API flow: `POST /api/proposals` → `POST /api/proposals/{id}/evaluate` → `POST /api/proposals/{id}/approval` → `POST /api/approvals/{approval_id}` with `{ "approve": true }` → `POST /api/approvals/{approval_id}/paypal/order` → buyer opens the returned `rel=approve` link → `POST /api/approvals/{approval_id}/paypal/capture`.

Run tests:

```powershell
C:/Users/MAHESH/anaconda3/python.exe -m pytest
```

The hardening layer adds SQLite persistence in `DATABASE_PATH`, registration/login, signed expiring bearer tokens, organization-scoped hashed API keys, durable idempotency keys, payment records, audit history, and verified PayPal webhook handling. Register with `POST /api/auth/register`, login with `POST /api/auth/login`, then create a developer key with authenticated `POST /api/orgs/api-keys`.

For a clean frontend setup, run `npm install` in `frontend/` once, then `npm run build` to verify the production bundle. If npm is unavailable or blocked, the backend and API demo can still be validated from `http://localhost:8000/docs`.

For Docker deployment, create `.env` first and run `docker compose up --build`. The backend database is stored in the `agentshield-data` volume.

This prototype uses an in-memory store, deterministic fallback intent extraction, sample products, and no live payment credentials. The PayPal boundary is intentionally not enabled until sandbox credentials and official API verification are configured.

## Safety boundary

The interpreter may extract intent, but it never authorizes payment. Only the deterministic policy engine can produce a decision. Approvals are single-use and fingerprint-bound; changing amount, product, merchant, or quantity invalidates the approval.

See [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md) and [docs/security/threat_model.md](docs/security/threat_model.md).
See the complete [hackathon readiness audit](docs/hackathon_readiness.md) for implemented, partial, and missing phases.

## GitHub-ready setup

### Repository structure

```text
AgentShield/
├── backend/                  # FastAPI API, policy engine, auth, PayPal adapter
│   ├── app/
│   └── requirements.txt
├── frontend/                 # React + TypeScript + Vite console
│   ├── src/
│   ├── package.json
│   └── .env.example
├── tests/                    # Backend policy, security, idempotency tests
├── docs/
│   ├── architecture/
│   ├── developer/
│   ├── reports/
│   └── demo/
├── .github/workflows/        # CI checks
├── Dockerfile
├── docker-compose.yml
├── .env.example              # Safe template only; never commit .env
└── README.md
```

### What to upload

Upload source code, documentation, tests, `frontend/package-lock.json`, screenshots, Docker files, CI configuration, and both `.env.example` files.

Do not upload `.env`, `agentshield.db`, `agentshield.db-shm`, `agentshield.db-wal`, `node_modules`, `frontend/dist`, Python caches, pytest caches, access tokens, PayPal credentials, or OpenAI keys. The repository `.gitignore` already excludes these runtime files.

### Environment configuration

Copy the templates before running:

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
```

Root `.env`:

```env
APP_NAME=AgentShield
APP_ENV=development
APP_SECRET_KEY=replace_with_a_long_random_secret
DATABASE_PATH=agentshield.db
OPENAI_API_KEY=replace_me
OPENAI_MODEL=gpt-4o-mini
PAYPAL_ENV=sandbox
PAYPAL_CLIENT_ID=replace_me
PAYPAL_CLIENT_SECRET=replace_me
PAYPAL_WEBHOOK_ID=replace_me
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
FRONTEND_URL=http://localhost:5174
```

Frontend `.env`:

```env
VITE_API_BASE_URL=http://localhost:8001
```

Never commit either `.env` file. Only commit `.env.example`.

### Local run on alternate ports

Terminal 1:

```powershell
cd D:\CMB_Desktop\AgentShield
C:/Users/MAHESH/anaconda3/python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
```

Terminal 2:

```powershell
cd D:\CMB_Desktop\AgentShield\frontend
npm install
npm run dev
```

Open the console at `http://localhost:5174`. Open API documentation at `http://localhost:8001/docs`.

### How the frontend and backend connect

```text
Browser: localhost:5174
        │ fetch() using VITE_API_BASE_URL
        ▼
FastAPI: localhost:8001
        │ validates request and calculates server-side amount
        ├── AI intent adapter
        ├── deterministic policy engine
        ├── SQLite persistence and audit log
        └── PayPal Sandbox OAuth / Orders API
```

The frontend never decides the final amount and never calls PayPal with secrets. The backend creates the PayPal order only after AgentShield approval.

### Demo flow

1. Enter: `Find a Bluetooth keyboard under ₹3,000. Ask me before checkout.`
2. Select the Bluetooth Wireless Keyboard.
3. Click **Evaluate proposal**.
4. Show `REQUIRE APPROVAL` and the rule explanations.
5. Click **Approve exact proposal**.
6. Create a PayPal Sandbox order.
7. Approve it with the PayPal Sandbox buyer account.
8. Capture it through the backend.
9. Show the audit event.
10. Repeat with the wired keyboard or premium keyboard and show `BLOCK`.

See the full [demo script](docs/demo/DEMO_SCRIPT.md) and [GitHub package checklist](docs/demo/GITHUB_PACKAGE.md).

## Demo screenshots

### AgentShield purchase guardrail

![AgentShield purchase guardrail showing the natural-language purchase request and demo catalogue](<Screenshot 2026-11-11 125300.png>)

### Policy evaluation and approval decision

![AgentShield policy evaluation showing the deterministic decision and approval workflow](<Screenshot 2026-11-11 125314.png>)

The images are stored in the repository root next to this README. Keep the filenames unchanged when uploading them to GitHub so these relative image links continue to render.
