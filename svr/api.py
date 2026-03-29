import os
import sys
import asyncio
import atexit
import subprocess
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpClt import run_mcp_operation, run_mcp_operation_container

_HERE          = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE  = os.path.join(_HERE, ".settings")
COMPOSE_FILE   = os.path.join(_HERE, "..", ".devcontainer", "docker-compose.yaml")
COMPOSE_PROJECT = "das_buddy"

CONTAINER_URLS = {
    "jira-svr": "http://localhost:8001",
    "post-svr":  "http://localhost:8002",
}

load_dotenv(SETTINGS_FILE, override=True)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

def get_openai_client():
    """Return a fresh OpenAI client using the current key from .settings."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Open Settings (⚙) and add your key."
        )
    return OpenAI(api_key=api_key)

SYSTEM_PROMPT = (
    "You are das_buddy, a helpful AI developer assistant. "
    "Answer clearly and concisely. Use markdown where helpful."
)

# ── Container lifecycle ───────────────────────────────────────────────────────

def _compose(*args):
    """Run a docker compose command and return (returncode, stdout, stderr)."""
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "-p", COMPOSE_PROJECT, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def start_containers():
    """Build images (if needed) and start both MCP server containers in the background."""
    print("[containers] Starting jira-svr and post-svr …")
    rc, out, err = _compose("up", "--build", "-d", "jira-svr", "post-svr")
    if rc != 0:
        print(f"[containers] WARNING: docker compose up failed (rc={rc})\n{err}")
    else:
        print("[containers] Both containers started.")


def stop_containers():
    """Stop both MCP server containers (called on app shutdown)."""
    print("[containers] Stopping jira-svr and post-svr …")
    _compose("stop", "jira-svr", "post-svr")
    print("[containers] Containers stopped.")


def _container_is_running(container_name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
        capture_output=True, text=True,
    )
    return result.stdout.strip() == "true"


# Start containers in a background thread so Flask boot isn't blocked
threading.Thread(target=start_containers, daemon=True).start()
atexit.register(stop_containers)

# ── Existing routes ───────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Empty message"}), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-20:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})

    try:
        completion = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        reply = completion.choices[0].message.content
        return jsonify({"response": reply})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mcp", methods=["POST"])
def mcp_tool():
    """Direct MCP tool call via stdio or container SSE.
    POST { server: 'jira-svr'|'post-svr', tool_name, arguments }
    Or legacy: POST { server_path, tool_name, arguments }
    """
    data = request.get_json(silent=True) or {}
    tool_name  = data.get("tool_name")
    arguments  = data.get("arguments", {})
    server_key = data.get("server")        # 'jira-svr' | 'post-svr'
    server_path = data.get("server_path")   # legacy stdio path

    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400

    try:
        if server_key and server_key in CONTAINER_URLS:
            result = asyncio.run(
                run_mcp_operation_container(CONTAINER_URLS[server_key], tool_name, arguments)
            )
        elif server_path:
            result = asyncio.run(run_mcp_operation(server_path, tool_name, arguments))
        else:
            return jsonify({"error": "Provide 'server' (container key) or 'server_path'"}), 400

        return jsonify({"result": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content})
    except FileNotFoundError:
        return jsonify({"content": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        load_dotenv(SETTINGS_FILE, override=True)
        return jsonify({"status": "saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Container status & control ────────────────────────────────────────────────

@app.route("/api/containers/status", methods=["GET"])
def containers_status():
    """Return running state of each MCP container."""
    return jsonify({
        name: _container_is_running(f"das_buddy-{name}")
        for name in CONTAINER_URLS
    })


@app.route("/api/containers/start", methods=["POST"])
def containers_start():
    threading.Thread(target=start_containers, daemon=True).start()
    return jsonify({"status": "starting"})


@app.route("/api/containers/stop", methods=["POST"])
def containers_stop():
    threading.Thread(target=stop_containers, daemon=True).start()
    return jsonify({"status": "stopping"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5001, debug=True)

