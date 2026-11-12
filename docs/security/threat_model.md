# Threat model

| Threat | Control |
|---|---|
| Amount tampering | Server calculates total from catalogue price |
| Wrong product | Category and structured feature rules |
| Prompt injection | External text is treated as data; interpreter cannot authorize |
| Approval replay | Approval is single-use and expires |
| Approval mutation | Fingerprint binds product, merchant, amount, currency, quantity, and proposal |
| Missing intent | Fail-closed `NEEDS_INFORMATION` decision |

This MVP does not claim production identity, durable storage, webhook verification, or live payment readiness.
