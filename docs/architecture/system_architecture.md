# System architecture

The MVP is a modular monolith: React console → FastAPI API → intent adapter + controlled catalogue → deterministic policy engine → approval store → audit events. The payment adapter is a future boundary and cannot be called directly by the interpreter or frontend.

The backend owns product price, totals, decisions, expiry, and approval fingerprints. A frontend amount is never accepted as authorization evidence.
