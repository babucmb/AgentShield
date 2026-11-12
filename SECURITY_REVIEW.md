# Security review checklist

Implemented in this submission pass:

- Passwords use PBKDF2-HMAC-SHA256 with per-password salts.
- JWTs are signed and expire after one hour.
- API keys are shown once and stored only as SHA-256 hashes.
- Proposal totals are calculated server-side.
- Approvals bind exact proposal fingerprints and expire.
- PayPal secrets remain server-side.
- Webhook event IDs are deduplicated durably.
- Idempotency responses are stored durably.
- Audit events are stored in SQLite instead of process memory.

Before production: rotate `APP_SECRET_KEY`, enforce HTTPS, add CSRF/session controls for browser auth, encrypt the database at rest, add rate limiting, verify PayPal signatures with the official verification endpoint, add dependency scanning, run penetration testing, and document privacy/retention obligations.

The production gate should fail if `APP_ENV=production` uses the development secret, if PayPal is configured for live credentials without an explicit deployment approval, or if the SQLite file is not on encrypted durable storage.
