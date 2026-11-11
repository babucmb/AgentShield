import re
from decimal import Decimal

from .schemas import Intent


def interpret(instruction: str) -> Intent:
    """Small deterministic fallback adapter; an LLM can implement this same contract later."""
    text = instruction.lower()
    budget_match = re.search(r"(?:under|below|less than|maximum|max)\s*[₹rs. ]*([\d,]+)", text)
    budget = Decimal(budget_match.group(1).replace(",", "")) if budget_match else None
    category = next((x for x in ("keyboard", "headphones", "laptop", "mouse") if x in text), None)
    features = {"connectivity": "Bluetooth"} if "bluetooth" in text else {}
    merchants = ["Amazon"] if "amazon" in text else []
    questions = []
    if not category:
        questions.append("Which product category should I purchase?")
    if budget is None:
        questions.append("What is the maximum budget?")
    return Intent(product_category=category, required_features=features, maximum_budget=budget,
                  allowed_merchants=merchants, requires_human_approval=("without approval" not in text),
                  confidence=0.92 if category and budget is not None else 0.55,
                  clarification_questions=questions)
