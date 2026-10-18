# auth — service d'authentification (Flask + Keycloak)

Gère la connexion via Keycloak (OpenID Connect) et expose une API pour que les autres
services vérifient les droits de l'utilisateur.

## Démarrage
```bash
docker network create web          # une seule fois, partagé avec les autres repos
cp .env.example .env               # puis remplir les valeurs
docker compose up -d --build
```

## Routes
| Route | Rôle |
|---|---|
| `GET /login?next=URL` | Redirige vers Keycloak, puis vers `next` |
| `GET /callback` | Retour OIDC (à déclarer dans Keycloak) |
| `GET /logout?next=URL` | Déconnexion (session locale + Keycloak) |
| `GET /api/me` | Utilisateur + rôles (401 si non connecté) |
| `GET /api/check?role=x&role=y&mode=any\|all` | 200 / 401 / 403 |
| `GET /health` | Healthcheck |

## Dans les autres repos
Le client est un package Python installable (dossier `client/`). Dans le `requirements.txt`
de chaque autre repo :
```
auth-client @ git+https://github.com/TON_USER/auth.git@v0.1.0#subdirectory=client
```
Puis :
```python
from auth_client import require_auth

@app.get("/admin")
@require_auth("admin")
def admin(): ...
```
- Le Dockerfile de l'autre repo doit avoir `git` (`apt-get install -y git`) pour installer depuis GitHub.
- Repo privé : utiliser un deploy token (`git+https://<token>@github.com/...`) ou une clé SSH via BuildKit.
- Versionner avec des tags git (`git tag v0.1.0 && git push --tags`) et mettre à jour le tag
  dans les repos consommateurs quand le client change.
- Variables d'environnement côté consommateur : `AUTH_INTERNAL_URL` et `AUTH_PUBLIC_URL`,
  et rejoindre le réseau Docker `web`.

## Important
- Les services doivent être sous le même domaine parent (ex. `auth.example.com`, `app.example.com`)
  et `SESSION_COOKIE_DOMAIN=.example.com` pour que le cookie soit partagé.
- Le cookie de session ne contient que l'identité et les rôles ; ils sont rafraîchis à
  chaque reconnexion (durée réglée par `SESSION_LIFETIME_MINUTES`).
