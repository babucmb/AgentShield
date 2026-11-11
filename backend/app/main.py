from datetime import timedelta, datetime, timezone
import hashlib, json
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .catalog import PRODUCTS, get_product
from .ai_provider import interpret_with_provider
from .paypal import PayPalClient, PayPalNotConfigured
from .auth import current_identity, issue_token, password_hash, password_matches
from .persistence import audit as persist_audit, audit_list, captured_total, create_organization, create_user, get_user, idempotent_response, init_db, issue_api_key, load_payloads, load_payments, load_policy, remember_webhook, save_idempotent_response, save_payload, save_payment, save_policy
from .policy import evaluate
from .schemas import APIKeyRequest, Approval, ApprovalAction, Evaluation, LoginRequest, Policy, Proposal, ProposalCreate, RegisterRequest

app = FastAPI(title="AgentShield API", version="0.1.0")
init_db()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
proposals: dict[str, Proposal] = {}
evaluations: dict[str, Evaluation] = {}
approvals: dict[str, Approval] = {}
audit_events: list[dict] = []
paypal_orders: dict[str, dict] = {}
policies: dict[str, Policy] = {"demo": Policy()}
if load_policy("demo"):
    policies["demo"] = Policy.model_validate(load_policy("demo"))

def record_audit(event: dict) -> None:
    audit_events.append(event)
    event_type = event.get("event", "unknown")
    persist_audit(event_type, {key: value for key, value in event.items() if key != "event"})

for _proposal in load_payloads("proposals"):
    proposals[str(_proposal["id"])] = Proposal.model_validate(_proposal)
for _evaluation in load_payloads("evaluations"):
    evaluations[str(_evaluation["proposal_id"])] = Evaluation.model_validate(_evaluation)
for _approval in load_payloads("approvals"):
    approvals[str(_approval["id"])] = Approval.model_validate(_approval)
for _payment in load_payments():
    paypal_orders[_payment["approval_id"]] = {"order_id": _payment["order_id"], "status": _payment["status"], **_payment["payload"]}

def fingerprint(proposal: Proposal) -> str:
    payload = {"product": proposal.product.id, "merchant": proposal.product.merchant, "amount": str(proposal.total_amount), "currency": proposal.product.currency, "quantity": proposal.quantity, "proposal": str(proposal.id)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

@app.post("/api/auth/register")
def register(request: RegisterRequest):
    if get_user(request.email): raise HTTPException(409, "Email is already registered")
    org_id = create_organization(request.organization_name)
    user_id = create_user(org_id, request.email, password_hash(request.password))
    return {"access_token": issue_token(user_id, org_id, "owner"), "token_type": "bearer", "organization_id": org_id}

@app.post("/api/auth/login")
def login(request: LoginRequest):
    user = get_user(request.email)
    if not user or not password_matches(request.password, user["password_hash"]): raise HTTPException(401, "Invalid email or password")
    return {"access_token": issue_token(user["id"], user["organization_id"], user["role"]), "token_type": "bearer"}

@app.post("/api/orgs/api-keys")
def create_api_key(request: APIKeyRequest, identity: dict = Depends(current_identity)):
    key_id, raw = issue_api_key(identity["org"], request.label)
    return {"id": key_id, "key": raw, "warning": "Store this key now; it cannot be retrieved again."}

@app.get("/api/me")
def me(identity: dict = Depends(current_identity)):
    return identity

@app.get("/api/policy", response_model=Policy)
def get_policy(identity: dict = Depends(current_identity)):
    return policies.get(identity["org"], policies["demo"])

@app.put("/api/policy", response_model=Policy)
def update_policy(policy: Policy, identity: dict = Depends(current_identity)):
    policies[identity["org"]] = policy
    # Legacy demo proposal endpoints use the demo workspace until proposal ownership
    # is fully migrated; keep the authenticated workspace policy effective there.
    policies["demo"] = policy
    save_policy(identity["org"], policy.model_dump(mode="json"))
    persist_audit("policy.updated", {"organization_id": identity["org"]})
    return policy

@app.get("/health")
def health(): return {"status": "ok", "service": "agentshield"}

@app.get("/api/catalog")
def catalog(): return PRODUCTS

@app.post("/api/proposals", response_model=Proposal)
def create_proposal(request: ProposalCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key:
        previous = idempotent_response(idempotency_key, "demo")
        if previous: return previous
    product = get_product(request.product_id)
    if not product: raise HTTPException(404, "Product not found")
    intent, provider = interpret_with_provider(request.instruction)
    now = datetime.now(timezone.utc)
    proposal = Proposal(instruction=request.instruction, intent=intent, product=product, quantity=request.quantity,
                        total_amount=product.price * request.quantity, expires_at=now + timedelta(minutes=15))
    proposals[str(proposal.id)] = proposal
    save_payload("proposals", str(proposal.id), proposal.model_dump(mode="json"))
    record_audit({"event": "proposal.created", "proposal_id": str(proposal.id), "ai_provider": provider, "at": now.isoformat()})
    response = proposal.model_dump(mode="json")
    if idempotency_key: save_idempotent_response(idempotency_key, "demo", response)
    return response

@app.post("/api/proposals/{proposal_id}/evaluate", response_model=Evaluation)
def evaluate_proposal(proposal_id: str):
    proposal = proposals.get(proposal_id)
    if not proposal: raise HTTPException(404, "Proposal not found")
    current_policy = policies.get("demo", Policy())
    spent = captured_total()
    result = evaluate(proposal, current_policy, spent_today=spent, spent_this_month=spent); evaluations[proposal_id] = result
    save_payload("evaluations", proposal_id, result.model_dump(mode="json"))
    record_audit({"event": "policy.evaluated", "proposal_id": proposal_id, "decision": result.decision, "at": result.evaluated_at.isoformat()})
    return result

@app.post("/api/proposals/{proposal_id}/approval", response_model=Approval)
def create_approval(proposal_id: str):
    proposal = proposals.get(proposal_id); result = evaluations.get(proposal_id)
    if not proposal or not result: raise HTTPException(404, "Proposal must be evaluated first")
    if result.decision not in ("REQUIRE_APPROVAL", "ALLOW"): raise HTTPException(409, "Proposal is not eligible for approval")
    approval = Approval(proposal_id=proposal.id, fingerprint=fingerprint(proposal), expires_at=result.expires_at)
    approvals[str(approval.id)] = approval
    save_payload("approvals", str(approval.id), approval.model_dump(mode="json"))
    record_audit({"event": "approval.created", "approval_id": str(approval.id), "proposal_id": proposal_id})
    return approval

@app.post("/api/approvals/{approval_id}", response_model=Approval)
def act_on_approval(approval_id: str, action: ApprovalAction):
    approval = approvals.get(approval_id)
    if not approval: raise HTTPException(404, "Approval not found")
    if approval.status != "PENDING": raise HTTPException(409, "Approval has already been decided")
    if approval.used or datetime.now(timezone.utc) >= approval.expires_at: raise HTTPException(409, "Approval is expired or already used")
    approval.status = "APPROVED" if action.approve else "REJECTED"
    save_payload("approvals", str(approval.id), approval.model_dump(mode="json"))
    record_audit({"event": "approval.decided", "approval_id": approval_id, "status": approval.status})
    return approval

@app.post("/api/approvals/{approval_id}/paypal/order")
def create_paypal_order(approval_id: str):
    approval = approvals.get(approval_id)
    if not approval or approval.status != "APPROVED": raise HTTPException(409, "An approved authorization is required")
    if approval.used or datetime.now(timezone.utc) >= approval.expires_at: raise HTTPException(409, "Authorization is expired or already used")
    proposal = proposals.get(str(approval.proposal_id))
    if not proposal or fingerprint(proposal) != approval.fingerprint: raise HTTPException(409, "Authorization no longer matches the proposal")
    try:
        order = PayPalClient().create_order(proposal.product, proposal.quantity, str(proposal.id))
    except PayPalNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "PayPal order creation failed") from exc
    paypal_orders[approval_id] = {"order_id": order["id"], "proposal_id": str(proposal.id), "status": order.get("status", "CREATED")}
    save_payment(approval_id, order["id"], order.get("status", "CREATED"), order)
    record_audit({"event": "paypal.order.created", "approval_id": approval_id, "order_id": order["id"]})
    return {"order_id": order["id"], "status": order.get("status"), "links": order.get("links", [])}

@app.post("/api/approvals/{approval_id}/paypal/capture")
def capture_paypal_order(approval_id: str):
    approval = approvals.get(approval_id); order = paypal_orders.get(approval_id)
    if not approval or approval.status != "APPROVED" or not order: raise HTTPException(409, "Create an approved PayPal order first")
    if approval.used: raise HTTPException(409, "Authorization has already been consumed")
    try:
        result = PayPalClient().capture_order(order["order_id"])
    except PayPalNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "PayPal capture failed; reconcile before retrying") from exc
    approval.used = True; order["status"] = result.get("status", "UNKNOWN")
    save_payload("approvals", str(approval.id), approval.model_dump(mode="json")); save_payment(approval_id, order["order_id"], order["status"], result)
    record_audit({"event": "paypal.order.captured", "approval_id": approval_id, "order_id": order["order_id"], "status": order["status"]})
    return result

@app.get("/api/audit")
def audit(): return audit_list()

@app.post("/api/webhooks/paypal")
async def paypal_webhook(request: Request):
    event = await request.json()
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        valid = PayPalClient().verify_webhook(headers, event)
    except PayPalNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "PayPal webhook verification failed") from exc
    if not valid: raise HTTPException(400, "Invalid PayPal webhook signature")
    event_id = event.get("id")
    if not event_id: raise HTTPException(400, "Webhook event id is required")
    if not remember_webhook(event_id, event.get("event_type", "unknown"), event): return {"status": "duplicate"}
    persist_audit("paypal.webhook.received", {"event_id": event_id, "event_type": event.get("event_type")})
    return {"status": "accepted"}
