import os
import sys
import asyncio
import atexit
import threading
import webbrowser
import time
import httpx
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# ── Bundle vs dev mode ────────────────────────────────────────────────────────
_FROZEN   = getattr(sys, "frozen", False)
_MEIPASS  = getattr(sys, "_MEIPASS", None)
_EXE_DIR  = os.path.dirname(sys.executable) if _FROZEN else None
_HERE     = os.path.dirname(os.path.abspath(__file__))

if not _FROZEN:
    sys.path.insert(0, _HERE)

from mcpClt import run_mcp_operation, run_mcp_operation_container

SETTINGS_FILE = os.path.join(_EXE_DIR or _HERE, ".settings")

_WEB_DIR = (
    os.path.join(_MEIPASS, "web")
    if _FROZEN
    else os.path.join(_HERE, "..", "clt", "dist")
)

load_dotenv(SETTINGS_FILE, override=True)

# ── MCP container URLs ────────────────────────────────────────────────────────
def _container_urls() -> dict:
    return {
        "jira-svr": os.getenv("JIRA_SVR_URL", "").rstrip("/"),
        "post-svr": os.getenv("POST_SVR_URL", "").rstrip("/"),
    }

# ── Codespace lifecycle ───────────────────────────────────────────────────────
_GH_API = "https://api.github.com"
_cs_lock  = threading.Lock()
_cs_name:  str | None = None
_cs_state: str = "idle"   # idle | creating | ready | error:<msg>


def _gh_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _set_state(state: str):
    global _cs_state
    _cs_state = state
    print(f"[codespace] {state}")


def _find_existing_codespace(repo: str) -> str | None:
    """Return the name of an existing non-deleted Codespace for *repo*, if any."""
    resp = httpx.get(f"{_GH_API}/user/codespaces", headers=_gh_headers(), timeout=10)
    if resp.status_code != 200:
        return None
    for cs in resp.json().get("codespaces", []):
        cs_repo = cs.get("repository", {}).get("full_name", "")
        if cs_repo.lower() == repo.lower() and cs.get("state") not in ("Deleted", "Failed"):
            return cs["name"]
    return None


def _codespace_lifecycle():
    """Background thread: create (or reuse) a Codespace, wait until ready, set URLs."""
    global _cs_name

    repo = os.getenv("CODESPACE_REPO", "").strip()
    if not repo:
        _set_state("idle")
        return

    _set_state("creating")
    try:
        # Re-use an existing Codespace for this repo if one exists
        existing = _find_existing_codespace(repo)
        if existing:
            _cs_name = existing
            print(f"[codespace] Reusing existing Codespace: {_cs_name}")
        else:
            resp = httpx.post(
                f"{_GH_API}/repos/{repo}/codespaces",
                headers=_gh_headers(),
                json={"ref": "main"},
                timeout=30,
            )
            if resp.status_code not in (200, 201):
                _set_state(f"error: create failed ({resp.status_code}) {resp.text[:120]}")
                return
            _cs_name = resp.json()["name"]
            print(f"[codespace] Created: {_cs_name}")

        # Poll until Available (up to 5 min)
        deadline = time.time() + 300
        while time.time() < deadline:
            r = httpx.get(
                f"{_GH_API}/user/codespaces/{_cs_name}",
                headers=_gh_headers(), timeout=10,
            )
            state = r.json().get("state", "Unknown")
            print(f"[codespace] State: {state}")
            if state == "Available":
                break
            if state in ("Deleted", "Failed", "ShuttingDown"):
                _set_state(f"error: Codespace entered state '{state}'")
                return
            time.sleep(10)
        else:
            _set_state("error: timed out waiting for Codespace to become Available")
            return

        # Make ports public so the local exe can call them without browser auth
        for port in [8001, 8002]:
            httpx.put(
                f"{_GH_API}/user/codespaces/{_cs_name}/ports/{port}/visibility",
                headers=_gh_headers(),
                json={"visibility": "public"},
                timeout=10,
            )

        # Inject the forwarded port URLs into the live environment
        os.environ["JIRA_SVR_URL"] = f"https://{_cs_name}-8001.app.github.dev"
        os.environ["POST_SVR_URL"] = f"https://{_cs_name}-8002.app.github.dev"
        _set_state("ready")

    except Exception as exc:
        _set_state(f"error: {exc}")


def _delete_codespace():
    """atexit handler: delete the Codespace that was created for this session."""
    global _cs_name
    if not _cs_name:
        return
    print(f"[codespace] Deleting {_cs_name} ...")
    try:
        httpx.delete(
            f"{_GH_API}/user/codespaces/{_cs_name}",
            headers=_gh_headers(), timeout=30,
        )
        print("[codespace] Deleted.")
    except Exception as exc:
        print(f"[codespace] Delete failed: {exc}")


# Start the lifecycle thread immediately on import; delete on clean exit
threading.Thread(target=_codespace_lifecycle, daemon=True).start()
atexit.register(_delete_codespace)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app, origins=[
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5001", "http://127.0.0.1:5001",
])

# ── Serve React frontend ──────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not os.path.isdir(_WEB_DIR):
        return "Frontend not built. Run: npm run build inside clt/", 503
    target = os.path.join(_WEB_DIR, path)
    if path and os.path.isfile(target):
        return send_from_directory(_WEB_DIR, path)
    return send_from_directory(_WEB_DIR, "index.html")

# ── GitHub Copilot ────────────────────────────────────────────────────────────

COPILOT_MODEL = "gpt-4o"
_copilot_cache: dict = {"token": None, "expires_at": 0.0}
_copilot_lock = threading.Lock()


def _exchange_for_copilot_token() -> tuple:
    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if not github_token:
        raise ValueError("GITHUB_TOKEN is not set. Open Settings (⚙) and add your GitHub.com classic PAT.")
    resp = httpx.get(
        "https://api.github.com/copilot_internal/v2/token",
        headers={"Authorization": f"Bearer {github_token}", "Accept": "application/json"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError(
            f"Copilot token exchange failed ({resp.status_code}): {resp.text[:300]}\n"
            "GITHUB_TOKEN must be a GitHub.com classic PAT. "
            "Generate one at https://github.com/settings/tokens"
        )
    data = resp.json()
    return data["token"], float(data.get("expires_at", time.time() + 1740))


def _get_cached_copilot_token() -> str:
    with _copilot_lock:
        if _copilot_cache["token"] and _copilot_cache["expires_at"] > time.time() + 60:
            return _copilot_cache["token"]
        token, expires_at = _exchange_for_copilot_token()
        _copilot_cache["token"] = token
        _copilot_cache["expires_at"] = expires_at
        return token


def get_copilot_client() -> OpenAI:
    session_token = _get_cached_copilot_token()
    return OpenAI(
        api_key=session_token,
        base_url="https://api.githubcopilot.com",
        default_headers={
            "Copilot-Integration-Id": "copilot-chat",
            "Editor-Version": "das_buddy/1.0.0",
            "Editor-Plugin-Version": "das_buddy-flask/1.0.0",
        },
    )


SYSTEM_PROMPT = (
    "You are das_buddy, a helpful AI developer assistant powered by GitHub Copilot. "
    "Answer clearly and concisely. Use markdown where helpful."
)

# ── API routes ────────────────────────────────────────────────────────────────

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
        completion = get_copilot_client().chat.completions.create(
            model=os.getenv("COPILOT_MODEL", COPILOT_MODEL), messages=messages,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mcp", methods=["POST"])
def mcp_tool():
    data = request.get_json(silent=True) or {}
    tool_name   = data.get("tool_name")
    arguments   = data.get("arguments", {})
    server_key  = data.get("server")
    server_path = data.get("server_path")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    urls = _container_urls()
    try:
        if server_key and server_key in urls and urls[server_key]:
            result = asyncio.run(run_mcp_operation_container(urls[server_key], tool_name, arguments))
        elif server_path:
            result = asyncio.run(run_mcp_operation(server_path, tool_name, arguments))
        else:
            return jsonify({"error": "Codespace not ready yet or server URL not configured"}), 503
        return jsonify({"result": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return jsonify({"content": f.read()})
    except FileNotFoundError:
        return jsonify({"content": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json(silent=True) or {}
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(data.get("content", ""))
        load_dotenv(SETTINGS_FILE, override=True)
        return jsonify({"status": "saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/codespace/status", methods=["GET"])
def codespace_status():
    urls = _container_urls()
    return jsonify({
        "state":    _cs_state,
        "name":     _cs_name,
        "jira_url": urls.get("jira-svr", ""),
        "post_url": urls.get("post-svr", ""),
    })


def _container_is_running(url: str) -> bool:
    if not url:
        return False
    try:
        r = httpx.get(f"{url}/health", timeout=3, follow_redirects=True)
        return r.status_code < 500
    except Exception:
        return False


@app.route("/api/containers/status", methods=["GET"])
def containers_status():
    urls = _container_urls()
    return jsonify({name: _container_is_running(url) for name, url in urls.items()})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    if _FROZEN:
        def _open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open_browser, daemon=True).start()
        print(f"[das_buddy] Running at http://localhost:{port}")
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        app.run(port=port, debug=True)

