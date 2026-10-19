"""Acces a l'API d'administration Keycloak (lecture des utilisateurs) via le compte de service du client.

Prerequis dans Keycloak : client -> "Client authentication" ON et "Service accounts roles" ON,
puis onglet "Service accounts roles" -> Assign role -> client "realm-management" -> `view-users`.
"""
import time

import requests
from flask import current_app

CACHE_SECONDS = 60

_token = {"value": None, "exp": 0.0}
_users = {"value": None, "exp": 0.0}


def _admin_token() -> str:
    now = time.time()
    if _token["value"] and now < _token["exp"] - 10:
        return _token["value"]
    cfg = current_app.config
    resp = requests.post(
        f"{cfg['ISSUER']}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cfg["KEYCLOAK_CLIENT_ID"],
            "client_secret": cfg["KEYCLOAK_CLIENT_SECRET"],
        },
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    _token["value"] = data["access_token"]
    _token["exp"] = now + int(data.get("expires_in", 60))
    return _token["value"]


def list_users() -> list[dict]:
    now = time.time()
    if _users["value"] is not None and now < _users["exp"]:
        return _users["value"]

    cfg = current_app.config
    headers = {"Authorization": f"Bearer {_admin_token()}"}
    url = f"{cfg['KEYCLOAK_URL']}/admin/realms/{cfg['KEYCLOAK_REALM']}/users"
    users, first, page = [], 0, 100
    while True:
        resp = requests.get(
            url, headers=headers, params={"first": first, "max": page, "enabled": "true"}, timeout=5
        )
        resp.raise_for_status()
        batch = resp.json()
        users += [
            {
                "id": u["id"],
                "username": u.get("username"),
                "firstName": u.get("firstName"),
                "lastName": u.get("lastName"),
            }
            for u in batch
        ]
        if len(batch) < page:
            break
        first += page

    _users["value"], _users["exp"] = users, now + CACHE_SECONDS
    return users
