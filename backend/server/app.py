from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.server.session import GameSession

load_dotenv()

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
app = FastAPI(title="Jev Playing Flipping Birds")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.websocket("/ws")
async def play_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    session = GameSession(websocket.send_json)
    runner = asyncio.create_task(session.run_forever())
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                await session.handle(message)
    except WebSocketDisconnect:
        pass
    finally:
        runner.cancel()
        await session.close()
        try:
            await runner
        except asyncio.CancelledError:
            pass


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
