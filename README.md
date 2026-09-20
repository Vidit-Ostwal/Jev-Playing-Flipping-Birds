# Jev Playing Flipping Birds

Local demo: TypeSafe Jev plays Flappy Bird through `flappy-bird-gymnasium`, with a browser UI that streams the live game.

This repo is built one goal at a time. **Goal 0 (scaffold) is the only completed step so far.**

## Setup

```bash
uv sync
cp .env.example .env
```

Put your TypeSafe early-access key in `.env` as `TYPESAFE_API_KEY` when you reach the Jev goals. The env and UI can be developed first with the random and heuristic agents.

## Run

Not wired up yet. Later goals add:

- a headless Gymnasium smoke script
- `uvicorn backend.app:app --reload`
- the spectator page at `http://127.0.0.1:8000`

## Layout

- `backend/` — game session, Jev policy, FastAPI server
- `frontend/` — spectator page
- `.env.example` — `TYPESAFE_API_KEY` template
- `pyproject.toml` / `uv.lock` — dependencies and locked versions
