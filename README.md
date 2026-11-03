# Cobalt-chat-back

API FastAPI de Cobalt Chat : messagerie temps réel dont les messages sont chiffrés en RSA (implémentation maison) avant d'être stockés en base SQLite.

## Lancer en local

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

Documentation interactive : http://localhost:8000/docs

## Tests

```bash
venv\Scripts\python -m pytest tests
```

## Docker

```bash
docker build -t cobalt-chat-api .
docker run -d -p 8000:8000 -v cobalt-data:/app/data -e JWT_SECRET="une-longue-chaine-aleatoire" cobalt-chat-api
```

## Configuration (variables d'environnement ou `.env`)

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cobalt_chat.db` | Base de données |
| `JWT_SECRET` | valeur de dev | Signature des jetons — **à changer en production** |
| `JWT_EXPIRE_MINUTES` | `10080` | Durée de validité des jetons |
| `RSA_KEY_BITS` | `1024` | Taille des clés RSA par conversation |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | Origines CORS (format JSON) |

## Architecture

- `src/modules/crypt` : RSA (Miller-Rabin, Euclide étendu, chiffrement par blocs), une paire de clés par conversation
- `src/modules/auth` : comptes, mots de passe PBKDF2, JWT
- `src/modules/chat` : conversations, messages chiffrés, réactions, accusés de lecture
- `src/core/realtime.py` : WebSocket (`/api/v1/ws`) pour messages, saisie et présence

Limites connues : RSA « textbook » sans padding OAEP ; le serveur chiffre et déchiffre, et les clés privées sont stockées dans la même base (chiffrement au repos, pas de bout-en-bout).
