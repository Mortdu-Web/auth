import os


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]

    KEYCLOAK_URL = os.environ["KEYCLOAK_URL"].rstrip("/")
    KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]
    KEYCLOAK_CLIENT_ID = os.environ["KEYCLOAK_CLIENT_ID"]
    KEYCLOAK_CLIENT_SECRET = os.environ["KEYCLOAK_CLIENT_SECRET"]

    URL_PREFIX = os.getenv("URL_PREFIX", "").rstrip("/")
    PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:5000").rstrip("/")
    DEFAULT_REDIRECT = os.getenv("DEFAULT_REDIRECT", "/")
    ALLOWED_REDIRECT_DOMAINS = [
        d.strip() for d in os.getenv("ALLOWED_REDIRECT_DOMAINS", "").split(",") if d.strip()
    ]
    BEHIND_PROXY = _bool("BEHIND_PROXY", False)

    # Cookie de session (signé par Flask). Domaine partagé => lisible par les autres sous-domaines.
    SESSION_COOKIE_NAME = "site_session"
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_MINUTES", "480")) * 60

    @property
    def ISSUER(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"
