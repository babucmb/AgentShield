import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


PAYPAL_BASE_URL = env("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET")
OPENAI_API_KEY = env("OPENAI_API_KEY") or env("LLM_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", env("LLM_MODEL", "gpt-4o-mini"))
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")
APP_ENV = env("APP_ENV", "development")
if APP_ENV == "production" and env("APP_SECRET_KEY", "development-only-change-me") in {"", "development-only-change-me", "replace_me"}:
    raise RuntimeError("APP_SECRET_KEY must be set to a non-development value in production")
