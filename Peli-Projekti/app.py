import json
from pathlib import Path
from threading import Lock
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
MENU_CONFIG_FILE = DATA_DIR / "menu_config.json"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"

app = Flask(__name__, static_folder="static", static_url_path="/static")
_lock = Lock()

DEFAULT_MENU_CONFIG = {
    "game_name": "Pelin nimi",
    "how_to_play": {
        "title": "How to play",
        "steps": [
            "Click Play to start the game.",
            "Click the left and right arrows to move between stages.",
            "Reach the end screen to finish your run.",
        ],
    },
}

DEFAULT_LEADERBOARD = []


def _read_json(path: Path, default):
    if not path.exists():
        return json.loads(json.dumps(default))
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return json.loads(json.dumps(default))
    return json.loads(raw)


def _write_json(path: Path, payload) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@app.get("/")
def serve_menu():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/menu.css")
def serve_menu_css():
    return send_from_directory(STATIC_DIR, "menu.css")

@app.get("/img/<path:filename>")
def serve_img(filename: str):
    return send_from_directory(STATIC_DIR / "img", filename)


@app.get("/api/menu")
def get_menu_data():
    with _lock:
        if not MENU_CONFIG_FILE.exists():
            config = json.loads(json.dumps(DEFAULT_MENU_CONFIG))
            _write_json(MENU_CONFIG_FILE, config)
        else:
            config = _read_json(MENU_CONFIG_FILE, DEFAULT_MENU_CONFIG)

        leaderboard = _read_json(LEADERBOARD_FILE, DEFAULT_LEADERBOARD)
        return jsonify({
            "game_name": config.get("game_name", "Pelin nimi"),
            "how_to_play": config.get("how_to_play", DEFAULT_MENU_CONFIG["how_to_play"]),
            "leaderboard": leaderboard,
        }), 200


@app.get("/api/how-to-play")
def get_how_to_play():
    with _lock:
        config = _read_json(MENU_CONFIG_FILE, DEFAULT_MENU_CONFIG)
        return jsonify(config.get("how_to_play", DEFAULT_MENU_CONFIG["how_to_play"])), 200


@app.get("/api/leaderboard")
def get_leaderboard():
    with _lock:
        return jsonify({"entries": _read_json(LEADERBOARD_FILE, DEFAULT_LEADERBOARD)}), 200


@app.post("/api/leaderboard")
def add_leaderboard_entry():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON body"}), 400

    player = str(payload.get("player", "")).strip()
    score = payload.get("score")

    if not player or len(player) > 30:
        return jsonify({"error": "player must be 1 to 30 characters"}), 400
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        return jsonify({"error": "score must be a non-negative integer"}), 400

    with _lock:
        entries = _read_json(LEADERBOARD_FILE, DEFAULT_LEADERBOARD)
        entries.append({"player": player, "score": score})
        entries.sort(key=lambda item: item["score"], reverse=True)
        top_entries = entries[:10]
        _write_json(LEADERBOARD_FILE, top_entries)

    return jsonify({"entries": top_entries}), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)