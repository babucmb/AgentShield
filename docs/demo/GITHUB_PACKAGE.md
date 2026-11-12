# GitHub upload checklist

## Include

- `backend/`
- `frontend/src/`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `tests/`
- `docs/`
- `.github/`
- `.env.example`
- `frontend/.env.example`
- `Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.gitignore`
- `README.md`
- `SECURITY.md`
- `SECURITY_REVIEW.md`
- `LICENSE`
- `Screenshot 2026-11-11 125300.png`
- `Screenshot 2026-11-11 125314.png`

## Exclude

- `.env` and `frontend/.env`
- `agentshield.db`, `*.db-shm`, `*.db-wal`
- `node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `.pytest_cache/`
- `.git/`
- API keys, tokens, secrets, personal buyer credentials, and private logs

## Before publishing

```powershell
git status --short
git diff -- .env .env.example frontend/.env frontend/.env.example
git add .
git status --short
```

Confirm no secret file or database appears before committing. Publishing to a remote requires explicit authorization.
