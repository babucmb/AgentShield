# Hackathon readiness audit

## Current status

| Area | Status | Evidence / remaining work |
|---|---|---|
| Natural-language AI extraction | Implemented | OpenAI JSON extraction when `OPENAI_API_KEY` is set; safe deterministic fallback otherwise |
| Product verification | Implemented | Server-owned three-product catalogue and structured feature checks |
| Deterministic policy engine | Implemented | Category, budget, features, merchant, currency, expiry; fail-closed decisions |
| Human approval | Implemented | Pending/approved/rejected state, expiry, exact proposal fingerprint, single-use consumption |
| PayPal OAuth + Orders v2 | Implemented in code | Needs PayPal Sandbox credentials and a real buyer approval/capture test |
| Frontend | Implemented for evaluation | Needs `npm install`; checkout buttons should be added for the final demo UI |
| Database persistence | Missing | Current store is process memory; acceptable for a short demo, not production |
| Authentication / organizations / API keys | Missing | Out of MVP scope but required for a commercial product |
| Webhook signature verification | Missing | Required before production; not required for the first local Sandbox demo |
| Durable audit / reconciliation | Partial | Audit events exist in memory; persistence and PayPal webhook reconciliation remain |
| Deployment / CI | Missing | Add after local Sandbox flow is proven |

## Recommended judge-facing story

AgentShield is not another shopping chatbot. It is a transaction authorization firewall: AI extracts the request, the server verifies the catalogue facts, a deterministic policy engine decides, and PayPal is unreachable until a human approves the exact proposal.

## Required final proof

1. Show the successful Bluetooth keyboard request and `REQUIRE_APPROVAL` result.
2. Approve the exact proposal.
3. Create a PayPal Sandbox order from the server and open its approval link.
4. Approve it with the PayPal personal Sandbox account.
5. Capture on the server and show the completed status.
6. Show a wrong-feature proposal and an over-budget proposal blocked without a PayPal order.
7. Change the proposal amount or product and show the old fingerprint cannot authorize it.

## Production caveat

This is a hackathon prototype. Before real money or customers: add authentication, a database, rate limiting, durable idempotency, webhook signature verification, reconciliation for uncertain captures, privacy/retention controls, and a formal security review.
