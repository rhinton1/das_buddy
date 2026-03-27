import os
import sys
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Make mcpClt importable from the same directory
sys.path.insert(0, os.path.dirname(__file__))
from mcpClt import run_mcp_operation

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are das_buddy, a helpful AI developer assistant. "
    "Answer clearly and concisely. Use markdown where helpful."
)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []   # [{role, content}, ...]

    if not message:
        return jsonify({"error": "Empty message"}), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Include previous turns for context (last 10 pairs max)
    for turn in history[-20:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        reply = completion.choices[0].message.content
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mcp", methods=["POST"])
def mcp_tool():
    """Direct MCP tool call — POST {server_path, tool_name, arguments}"""
    data = request.get_json(silent=True) or {}
    server_path = data.get("server_path")
    tool_name = data.get("tool_name")
    arguments = data.get("arguments", {})

    if not server_path or not tool_name:
        return jsonify({"error": "server_path and tool_name are required"}), 400

    try:
        result = asyncio.run(run_mcp_operation(server_path, tool_name, arguments))
        return jsonify({"result": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5001, debug=True)

