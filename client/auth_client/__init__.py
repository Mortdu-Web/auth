"""
Client d'authentification à installer dans les autres services Flask :
    pip install "auth-client @ git+https://github.com/TON_USER/auth.git@v0.1.0#subdirectory=client"

Variables d'environnement à définir dans l'autre service :
  AUTH_INTERNAL_URL = http://auth:5000            (réseau Docker partagé)
  AUTH_PUBLIC_URL   = https://auth.example.com    (pour rediriger vers /login)

Usage :
    from auth_client import require_auth

    @app.get("/admin")
    @require_auth("admin")                 # rôle admin obligatoire
    def admin(): ...

    @app.get("/espace")
    @require_auth()                        # simplement connecté
    def espace(): ...

    @app.get("/redaction")
    @require_auth("editor", "admin")       # editor OU admin
    def redaction(): ...

    @app.get("/super")
    @require_auth("a", "b", mode="all")    # a ET b
    def super(): ...

L'utilisateur est ensuite disponible via flask.g.user.
"""
import os
from functools import wraps
from urllib.parse import quote

import requests
from flask import abort, g, jsonify, redirect, request

AUTH_INTERNAL_URL = os.environ.get("AUTH_INTERNAL_URL", "http://auth:5000").rstrip("/")
AUTH_PUBLIC_URL = os.environ.get("AUTH_PUBLIC_URL", "http://localhost:5000").rstrip("/")


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def require_auth(*roles: str, mode: str = "any"):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            headers = {}
            if request.headers.get("Cookie"):
                headers["Cookie"] = request.headers["Cookie"]
            if request.headers.get("Authorization"):
                headers["Authorization"] = request.headers["Authorization"]

            try:
                resp = requests.get(
                    f"{AUTH_INTERNAL_URL}/api/check",
                    params={"role": list(roles), "mode": mode},
                    headers=headers,
                    timeout=3,
                )
            except requests.RequestException:
                abort(503, "Service d'authentification indisponible")

            if resp.status_code == 401:
                if _wants_json():
                    return jsonify(error="not_authenticated"), 401
                return redirect(f"{AUTH_PUBLIC_URL}/login?next={quote(request.url, safe='')}")
            if resp.status_code == 403:
                abort(403)
            if resp.status_code != 200:
                abort(502)

            g.user = resp.json()["user"]
            return view(*args, **kwargs)

        return wrapper

    return decorator
