from urllib.parse import urlencode

import jwt
import requests
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from . import keycloak_admin
from .security import current_user, is_safe_redirect, user_from_claims

bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="keycloak",
        client_id=app.config["KEYCLOAK_CLIENT_ID"],
        client_secret=app.config["KEYCLOAK_CLIENT_SECRET"],
        server_metadata_url=f"{app.config['ISSUER']}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )


# ---------------------------------------------------------------- Flux navigateur
@bp.get("/login")
def login():
    nxt = request.args.get("next")
    session["next"] = nxt if is_safe_redirect(nxt) else current_app.config["DEFAULT_REDIRECT"]
    redirect_uri = f"{current_app.config['PUBLIC_URL']}{url_for('auth.callback')}"
    return oauth.keycloak.authorize_redirect(redirect_uri)


@bp.get("/callback")
def callback():
    token = oauth.keycloak.authorize_access_token()
    client_id = current_app.config["KEYCLOAK_CLIENT_ID"]
    # Le token vient directement de Keycloak (canal back-channel TLS) : on lit les claims
    # de l'access token pour récupérer les rôles.
    access_claims = jwt.decode(token["access_token"], options={"verify_signature": False})
    claims = {**token.get("userinfo", {}), **access_claims}

    session.permanent = True
    session["user"] = user_from_claims(claims, client_id)
    return redirect(session.pop("next", current_app.config["DEFAULT_REDIRECT"]))


@bp.get("/logout")
def logout():
    session.clear()
    metadata = oauth.keycloak.load_server_metadata()
    nxt = request.args.get("next")
    target = nxt if is_safe_redirect(nxt) else current_app.config["DEFAULT_REDIRECT"]
    params = urlencode(
        {
            "client_id": current_app.config["KEYCLOAK_CLIENT_ID"],
            "post_logout_redirect_uri": target,
        }
    )
    return redirect(f"{metadata['end_session_endpoint']}?{params}")


# ---------------------------------------------------------------- API pour les autres services
@bp.get("/api/me")
def me():
    """Retourne l'utilisateur connecté et ses rôles, ou 401."""
    user = current_user()
    if not user:
        return jsonify(authenticated=False), 401
    return jsonify(authenticated=True, user=user)


@bp.get("/api/check")
def check():
    """
    Vérifie l'accès. Exemples :
      /api/check                          -> juste connecté ?
      /api/check?role=admin               -> doit avoir le rôle admin
      /api/check?role=admin&role=editor   -> admin OU editor   (mode=any, défaut)
      /api/check?role=a&role=b&mode=all   -> a ET b
    Codes : 200 autorisé, 401 non connecté, 403 connecté mais interdit.
    """
    user = current_user()
    if not user:
        return jsonify(authorized=False, reason="not_authenticated"), 401

    required = request.args.getlist("role")
    if required:
        owned = set(user["roles"])
        mode = request.args.get("mode", "any")
        ok = owned.issuperset(required) if mode == "all" else bool(owned & set(required))
        if not ok:
            return jsonify(authorized=False, reason="forbidden", required=required), 403

    return jsonify(authorized=True, user=user)


@bp.get("/api/users")
def users():
    """Liste des utilisateurs Keycloak actifs (id, username, firstName, lastName). Reserve aux connectes."""
    if not current_user():
        return jsonify(error="not_authenticated"), 401
    try:
        return jsonify(users=keycloak_admin.list_users())
    except requests.RequestException:
        current_app.logger.exception("Keycloak injoignable ou droits insuffisants (view-users)")
        return jsonify(error="keycloak_unavailable"), 502


@bp.get("/health")
def health():
    return jsonify(status="ok")
