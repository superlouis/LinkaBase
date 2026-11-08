# Linkabase

A self-hosted project space for tasks, topics, wiki pages, and diagrams. Full setup, deployment, encrypted project transfers, and backup instructions are in [the application README](linkabase/README.md).

Run directly with uv:

```bash
cd linkabase
uv sync --frozen
uv run python main.py start
```

Or build and run both services with Docker Compose:

```bash
cd linkabase
docker compose up -d --build
docker compose logs --tail=100
```

Open http://localhost:8501 locally. If configuring `.env`, create it from `linkabase/.env.example` only when it does not already exist. Stop uv services before running Docker on the same ports/workspace. See [the security review](linkabase/SECURITY_REVIEW.md) before public deployment.
