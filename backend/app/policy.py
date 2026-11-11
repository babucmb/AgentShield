from datetime import datetime, timezone
from .schemas import Decision, Evaluation, Policy, Proposal, RuleResult


def evaluate(proposal: Proposal, policy: Policy | None = None, spent_today: float = 0, spent_this_month: float = 0) -> Evaluation:
    now = datetime.now(timezone.utc)
    policy = policy or Policy()
    rules: list[RuleResult] = []
    reasons: list[str] = []
    intent, product = proposal.intent, proposal.product
    if not policy.active:
        return Evaluation(proposal_id=proposal.id, decision=Decision.BLOCK, rules=[RuleResult(name="policy_active", passed=False, detail="The organization policy is inactive.")], reasons=["Purchasing is disabled by the organization policy."], expires_at=proposal.expires_at)
    if not intent.product_category or intent.maximum_budget is None:
        rules.append(RuleResult(name="complete_intent", passed=False, detail="Category and budget are required."))
        return Evaluation(proposal_id=proposal.id, decision=Decision.NEEDS_INFORMATION, rules=rules,
                          reasons=["Complete the purchase requirements before checkout."], expires_at=proposal.expires_at)
    category_ok = product.category == intent.product_category
    rules.append(RuleResult(name="category_match", passed=category_ok, detail=f"Expected {intent.product_category}; got {product.category}."))
    if not category_ok: reasons.append("The product category does not match the request.")
    budget_ok = proposal.total_amount <= min(intent.maximum_budget, policy.max_transaction_amount)
    rules.append(RuleResult(name="budget", passed=budget_ok, detail=f"Total {proposal.total_amount} vs maximum {intent.maximum_budget}."))
    if not budget_ok: reasons.append(f"The product exceeds the maximum budget by {proposal.total_amount - intent.maximum_budget}.")
    feature_ok = all(product.features.get(k, "").lower() == v.lower() for k, v in intent.required_features.items())
    rules.append(RuleResult(name="required_features", passed=feature_ok, detail="Required product attributes match." if feature_ok else "Required product attributes are missing or different."))
    if not feature_ok: reasons.append("The product does not satisfy the required features.")
    merchant_ok = (not intent.allowed_merchants or product.merchant.lower() in {m.lower() for m in intent.allowed_merchants}) and (not policy.allowed_merchants or product.merchant.lower() in {m.lower() for m in policy.allowed_merchants}) and product.merchant.lower() not in {m.lower() for m in policy.blocked_merchants}
    rules.append(RuleResult(name="merchant", passed=merchant_ok, detail="Merchant is allowed." if merchant_ok else "Merchant is not on the allowlist."))
    if not merchant_ok: reasons.append("The merchant is not approved for this request.")
    currency_ok = product.currency == intent.currency and product.currency in policy.allowed_currencies
    rules.append(RuleResult(name="currency", passed=currency_ok, detail=f"Currency is {product.currency}."))
    if not currency_ok: reasons.append("The currency is not supported by the intent.")
    if now >= proposal.expires_at:
        reasons.append("The proposal has expired.")
    quantity_ok = proposal.quantity <= policy.max_quantity
    rules.append(RuleResult(name="quantity", passed=quantity_ok, detail=f"Quantity {proposal.quantity} vs maximum {policy.max_quantity}."))
    if not quantity_ok: reasons.append("The requested quantity exceeds the policy limit.")
    daily_ok = spent_today + float(proposal.total_amount) <= float(policy.daily_spending_limit)
    monthly_ok = spent_this_month + float(proposal.total_amount) <= float(policy.monthly_spending_limit)
    rules.extend([RuleResult(name="daily_limit", passed=daily_ok, detail=f"Projected daily spend {spent_today + float(proposal.total_amount)} vs {policy.daily_spending_limit}."), RuleResult(name="monthly_limit", passed=monthly_ok, detail=f"Projected monthly spend {spent_this_month + float(proposal.total_amount)} vs {policy.monthly_spending_limit}.")])
    if not daily_ok: reasons.append("The daily spending limit would be exceeded.")
    if not monthly_ok: reasons.append("The monthly spending limit would be exceeded.")
    category_ok = category_ok and product.category.lower() not in {c.lower() for c in policy.restricted_categories}
    all_pass = all(r.passed for r in rules) and category_ok and now < proposal.expires_at
    decision = Decision.REQUIRE_APPROVAL if all_pass and (intent.requires_human_approval or policy.requires_human_approval) else Decision.ALLOW if all_pass else Decision.BLOCK
    if not reasons and decision == Decision.REQUIRE_APPROVAL: reasons.append("All rules passed; explicit user approval is required.")
    return Evaluation(proposal_id=proposal.id, decision=decision, rules=rules, reasons=reasons, expires_at=proposal.expires_at)
