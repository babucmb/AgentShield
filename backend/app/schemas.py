from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"


class Intent(BaseModel):
    product_category: str | None = None
    required_features: dict[str, str] = Field(default_factory=dict)
    maximum_budget: Decimal | None = None
    currency: str = "INR"
    allowed_merchants: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True
    confidence: float = Field(ge=0, le=1, default=0.7)
    clarification_questions: list[str] = Field(default_factory=list)


class Product(BaseModel):
    id: str
    name: str
    category: str
    price: Decimal
    currency: str = "INR"
    merchant: str
    features: dict[str, str] = Field(default_factory=dict)


class ProposalCreate(BaseModel):
    instruction: str = Field(min_length=3)
    product_id: str
    quantity: int = Field(default=1, ge=1, le=20)


class Proposal(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(default_factory=uuid4)
    instruction: str
    intent: Intent
    product: Product
    quantity: int
    total_amount: Decimal
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime


class RuleResult(BaseModel):
    name: str
    passed: bool
    detail: str


class Evaluation(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    decision: Decision
    policy_version: str = "demo-v1"
    rules: list[RuleResult]
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime


class Approval(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    fingerprint: str
    status: str = "PENDING"
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalAction(BaseModel):
    approve: bool


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    organization_name: str = Field(default="My AgentShield Workspace", min_length=2)


class LoginRequest(BaseModel):
    email: str
    password: str


class APIKeyRequest(BaseModel):
    label: str = Field(default="developer", min_length=1, max_length=80)


class Policy(BaseModel):
    max_transaction_amount: Decimal = Decimal("3000")
    daily_spending_limit: Decimal = Decimal("10000")
    monthly_spending_limit: Decimal = Decimal("50000")
    allowed_merchants: list[str] = Field(default_factory=list)
    blocked_merchants: list[str] = Field(default_factory=list)
    allowed_currencies: list[str] = Field(default_factory=lambda: ["INR"])
    restricted_categories: list[str] = Field(default_factory=list)
    max_quantity: int = Field(default=5, ge=1, le=100)
    requires_human_approval: bool = True
    active: bool = True
