"""HTTP + WebSocket smoke test for the spectator server."""

from starlette.testclient import TestClient

from backend.server.app import app


def _first_frame(ws, limit: int = 30) -> dict:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == "frame":
            return msg
    raise RuntimeError("no frame received")


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200 and health.json()["ok"] is True
    assert client.get("/").status_code == 200
    assert client.get("/styles.css").status_code == 200
    assert client.get("/app.js").status_code == 200

    for agent in ("random", "heuristic", "jev"):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "start", "agent": agent, "fallback": True})
            frame = _first_frame(ws)
            assert frame["image"]
            assert frame["action"] in {"flap", "noop"}
            assert isinstance(frame["score"], int)
            print(
                f"ws_ok agent={agent} action={frame['action']} "
                f"source={frame['source']} fallback={frame['fallback']} "
                f"image_bytes={len(frame['image'])}"
            )
            ws.send_json({"type": "pause"})
            ws.send_json({"type": "reset"})


if __name__ == "__main__":
    main()
