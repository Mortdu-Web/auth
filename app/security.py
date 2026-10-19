"""Outils : extraction des rôles, validation de Bearer token, redirections sûres."""
from urllib.parse import urlparse

import jwt
from flask import current_app, request, session
from jwt import PyJWKClient

_jwk_client: PyJWKClient | None = None


def extract_roles(claims: dict, client_id: str) -> list[str]:
    """Rôles du client + rôles du realm + groupes (si mapper 'groups' activé)."""
    roles = set(claims.get("resource_access", {}).get(client_id, {}).get("roles", []))
    roles |= set(claims.get("realm_access", {}).get("roles", []))
    return sorted(roles)


def user_from_claims(claims: dict, client_id: str) -> dict:
    return {
        "sub": claims.get("sub"),
        "username": claims.get("preferred_username"),
        "email": claims.get("email"),
        "name": claims.get("name"),
        "given_name": claims.get("given_name"),
        "family_name": claims.get("family_name"),
        "roles": extract_roles(claims, client_id),
        "groups": claims.get("groups", []),
    }


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        issuer = current_app.config["ISSUER"]
        _jwk_client = PyJWKClient(f"{issuer}/protocol/openid-connect/certs", cache_keys=True)
    return _jwk_client


def verify_bearer(token: str) -> dict | None:
    """Valide un access token Keycloak (signature, expiration, issuer)."""
    try:
        key = _get_jwk_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=current_app.config["ISSUER"],
            options={"verify_aud": False},  # l'audience par défaut est "account"
        )
        return user_from_claims(claims, current_app.config["KEYCLOAK_CLIENT_ID"])
    except Exception:
        return None


def current_user() -> dict | None:
    """Utilisateur courant : session (cookie) ou header Authorization: Bearer."""
    user = session.get("user")
    if user:
        return user
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return verify_bearer(header[7:].strip())
    return None


def is_safe_redirect(url: str | None) -> bool:
    """Autorise les chemins relatifs et les domaines whitelistés uniquement."""
    if not url:
        return False
    if url.startswith("/") and not url.startswith("//"):
        return True
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    allowed = current_app.config["ALLOWED_REDIRECT_DOMAINS"]
    return any(parsed.hostname == d or parsed.hostname.endswith("." + d) for d in allowed)
