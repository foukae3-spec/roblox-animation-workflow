#!/usr/bin/env python3
"""Google AI Studio Local Bridge Server.

Provides a lightweight local web dashboard and REST API for Google AI Studio.
Allows users in Google AI Studio's web UI to easily execute function calls locally
and copy responses back into the AI Studio prompt runner.
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.roblox_tools import (
    build_blender_scene,
    create_new_episode,
    find_blender,
    generate_voiceover,
    get_engine_vocabulary,
    inspect_frame,
    render_contact_sheet,
    render_thumbnail,
    render_video_pipeline,
    validate_shotlist,
)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Google AI Studio - Roblox Animation Tools Bridge</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --accent: #38bdf8;
      --accent-hover: #7dd3fc;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --code-bg: #0b1120;
    }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; line-height: 1.5; }
    .container { max-width: 980px; margin: 0 auto; background: var(--card-bg); border-radius: 14px; padding: 28px; box-shadow: 0 12px 30px rgba(0,0,0,0.5); border: 1px solid var(--card-border); }
    header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 1px solid var(--card-border); padding-bottom: 16px; }
    h1 { margin: 0; color: var(--accent); font-size: 26px; }
    .subtitle { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
    .badge-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .badge { display: inline-flex; align-items: center; background: #0369a1; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
    .badge.green { background: #059669; }
    .tabs { display: flex; gap: 10px; margin: 20px 0 16px; border-bottom: 2px solid var(--card-border); }
    .tab { background: transparent; border: none; color: var(--text-muted); padding: 10px 18px; font-size: 15px; font-weight: 600; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
    .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .card { background: #162032; padding: 18px; border-radius: 10px; border: 1px solid var(--card-border); margin-bottom: 18px; }
    label { font-weight: 600; display: block; margin-bottom: 6px; font-size: 14px; color: var(--text); }
    select, input, textarea { width: 100%; background: var(--code-bg); border: 1px solid var(--card-border); color: var(--text); padding: 12px; border-radius: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; margin-bottom: 14px; }
    select:focus, input:focus, textarea:focus { border-color: var(--accent); outline: none; }
    .btn-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
    button { background: var(--accent); color: #0f172a; border: none; padding: 11px 20px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: background 0.15s ease-in-out; font-size: 14px; }
    button:hover { background: var(--accent-hover); }
    button.secondary { background: #475569; color: #fff; }
    button.secondary:hover { background: #64748b; }
    button.outline { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
    button.outline:hover { background: rgba(56, 189, 248, 0.1); }
    pre { background: var(--code-bg); padding: 14px; border-radius: 8px; overflow-x: auto; color: #a5f3fc; font-size: 12px; max-height: 400px; border: 1px solid var(--card-border); font-family: ui-monospace, SFMono-Regular, monospace; }
    .output-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .quick-links { display: flex; gap: 10px; margin-top: 14px; font-size: 13px; }
    .quick-links a { color: var(--accent); text-decoration: none; }
    .quick-links a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <span class="badge">Google AI Studio Local Bridge</span>
        <h1>Roblox 3D Animation Tools Bridge</h1>
        <div class="subtitle">Direct interface between Google AI Studio's Gemini models and local Blender 3D animation engine.</div>
      </div>
      <div id="statusBadges" class="badge-bar">
        <span class="badge green" id="blenderStatus">Blender: Checking...</span>
      </div>
    </header>

    <div class="tabs">
      <button class="tab active" onclick="switchTab('pasteTab', this)">📥 Paste AI Studio Tool Call</button>
      <button class="tab" onclick="switchTab('manualTab', this)">🛠️ Interactive Tool Runner</button>
      <button class="tab" onclick="switchTab('importTab', this)">📋 Export / Import Schemas</button>
    </div>

    <!-- Tab 1: Paste from Google AI Studio -->
    <div id="pasteTab" class="tab-content active">
      <div class="card">
        <label for="rawCallInput">Paste Function Call JSON from Google AI Studio Chat:</label>
        <textarea id="rawCallInput" rows="6" placeholder='e.g. {"name": "validate_shotlist", "args": {"episode_path": "episodes/wi_zlatan_bff"}}&#10;or {"functionCall": {"name": "get_engine_vocabulary", "args": {}}}'></textarea>
        <div class="btn-row">
          <button onclick="executeRawCall()">⚡ Execute Call</button>
          <button class="secondary" onclick="clearInput()">Clear</button>
        </div>
      </div>
    </div>

    <!-- Tab 2: Manual Interactive Tool Runner -->
    <div id="manualTab" class="tab-content">
      <div class="card">
        <label for="toolSelect">Select Tool:</label>
        <select id="toolSelect" onchange="updateDefaultArgs()">
          <option value="get_engine_vocabulary">get_engine_vocabulary()</option>
          <option value="validate_shotlist">validate_shotlist(episode_path)</option>
          <option value="create_new_episode">create_new_episode(episode_id, title, format_name, script_markdown, shots_data)</option>
          <option value="generate_voiceover">generate_voiceover(episode_path)</option>
          <option value="build_blender_scene">build_blender_scene(episode_path)</option>
          <option value="render_contact_sheet">render_contact_sheet(episode_path)</option>
          <option value="render_video_pipeline">render_video_pipeline(episode_path, final, only_stages, from_stage)</option>
          <option value="render_thumbnail">render_thumbnail(episode_path)</option>
          <option value="inspect_frame">inspect_frame(episode_path, frame_number)</option>
        </select>

        <label for="argsInput">Arguments (JSON):</label>
        <textarea id="argsInput" rows="6">{}</textarea>

        <div class="btn-row">
          <button onclick="executeSelectedTool()">Execute Tool</button>
        </div>
      </div>
    </div>

    <!-- Tab 3: Export / Import Schemas -->
    <div id="importTab" class="tab-content">
      <div class="card">
        <label>Google AI Studio Integration Resources:</label>
        <p style="color:var(--text-muted); font-size:13px;">Use these resources to configure tools and system prompts in the Google AI Studio web interface (aistudio.google.com):</p>
        <div class="btn-row">
          <button class="secondary" onclick="copyUrl('/openapi.json')">Copy OpenAPI 3.0 Spec URL</button>
          <button class="secondary" onclick="fetchAndCopy('/openapi.json')">Copy OpenAPI 3.0 JSON</button>
          <button class="secondary" onclick="fetchAndCopy('/ai_studio/tools_schema.json')">Copy Gemini Tools Schema</button>
          <button class="secondary" onclick="fetchAndCopy('/ai_studio/system_prompt.txt')">Copy System Prompt</button>
        </div>
        <div class="quick-links">
          <span>Raw Links:</span>
          <a href="/openapi.json" target="_blank">openapi.json</a> &bull;
          <a href="/ai_studio/tools_schema.json" target="_blank">tools_schema.json</a> &bull;
          <a href="/ai_studio/system_prompt.txt" target="_blank">system_prompt.txt</a> &bull;
          <a href="/api/status" target="_blank">status.json</a>
        </div>
      </div>
    </div>

    <!-- Output Box (Common to all tabs) -->
    <div class="card">
      <div class="output-header">
        <label style="margin:0;">Execution Result:</label>
        <div class="btn-row" style="margin:0;">
          <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="copyOutput('functionResponse')">📋 Copy for AI Studio (functionResponse)</button>
          <button class="secondary" style="padding:6px 12px; font-size:12px;" onclick="copyOutput('result')">Copy Raw Result</button>
        </div>
      </div>
      <pre id="outputBox">// Tool execution outputs and Gemini function responses will appear here...</pre>
    </div>
  </div>

  <script>
    let latestResponse = null;

    const sampleArgs = {
      "get_engine_vocabulary": "{}",
      "validate_shotlist": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "create_new_episode": JSON.stringify({
        "episode_id": "wi_demo",
        "title": "What If Roblox Characters Won The Cup?",
        "format_name": "what_if",
        "script_markdown": "# What If Roblox Characters Won The Cup?\\n\\nCast: Theo, Zlatan",
        "shots_data": {
          "episode": "wi_demo",
          "title": "What If Roblox Characters Won The Cup?",
          "format": "what_if",
          "music": "quirky",
          "hook_title": "WHAT IF WE WON?",
          "shots": [
            {
              "id": "s1",
              "set": "bedroom",
              "speaker": "narrator",
              "text": "What if Zlatan played in Roblox?",
              "camera": {"shot": "medium", "angle": "eye", "move": "static"},
              "cast": [{"name": "Theo", "mark": "center", "action": "talk"}]
            }
          ]
        }
      }, null, 2),
      "generate_voiceover": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "build_blender_scene": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "render_contact_sheet": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "render_video_pipeline": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff", "final": false}, null, 2),
      "render_thumbnail": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "inspect_frame": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff", "frame_number": 30}, null, 2)
    };

    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }

    function updateDefaultArgs() {
      const tool = document.getElementById("toolSelect").value;
      document.getElementById("argsInput").value = sampleArgs[tool] || "{}";
    }

    function clearInput() {
      document.getElementById("rawCallInput").value = "";
    }

    async function executeSelectedTool() {
      const tool = document.getElementById("toolSelect").value;
      const argsStr = document.getElementById("argsInput").value;
      let argsObj = {};
      try {
        argsObj = JSON.parse(argsStr || "{}");
      } catch(e) {
        alert("Invalid JSON in arguments: " + e.message);
        return;
      }
      await callBackend({ tool: tool, args: argsObj });
    }

    async function executeRawCall() {
      const raw = document.getElementById("rawCallInput").value.trim();
      if (!raw) {
        alert("Please paste a function call JSON payload first.");
        return;
      }
      let payload;
      try {
        payload = JSON.parse(raw);
      } catch(e) {
        alert("Invalid JSON payload: " + e.message);
        return;
      }
      await callBackend(payload);
    }

    async function callBackend(payload) {
      document.getElementById("outputBox").innerText = "Executing tool call...";
      try {
        const resp = await fetch("/api/call", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const data = await resp.json();
        latestResponse = data;
        document.getElementById("outputBox").innerText = JSON.stringify(data, null, 2);
      } catch(err) {
        document.getElementById("outputBox").innerText = "Error: " + err;
      }
    }

    function copyOutput(type) {
      if (!latestResponse) {
        alert("No output to copy yet.");
        return;
      }
      let text = "";
      if (type === 'functionResponse' && latestResponse.functionResponse) {
        text = JSON.stringify(latestResponse.functionResponse, null, 2);
      } else if (type === 'result' && latestResponse.result !== undefined) {
        text = JSON.stringify(latestResponse.result, null, 2);
      } else {
        text = JSON.stringify(latestResponse, null, 2);
      }
      navigator.clipboard.writeText(text);
      alert("Copied to clipboard!");
    }

    function copyUrl(path) {
      const url = window.location.origin + path;
      navigator.clipboard.writeText(url);
      alert("URL copied: " + url);
    }

    async function fetchAndCopy(path) {
      try {
        const r = await fetch(path);
        const text = await r.text();
        navigator.clipboard.writeText(text);
        alert(path + " contents copied to clipboard!");
      } catch(e) {
        alert("Failed to copy: " + e);
      }
    }

    // Check status on load
    window.addEventListener("DOMContentLoaded", async () => {
      try {
        const res = await fetch("/api/status");
        const status = await res.json();
        if (status.blender_found) {
          document.getElementById("blenderStatus").innerText = "Blender: " + status.blender_version;
        } else {
          document.getElementById("blenderStatus").innerText = "Blender: Not Found";
          document.getElementById("blenderStatus").style.background = "#dc2626";
        }
      } catch(e) {}
    });
  </script>
</body>
</html>
"""


class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")
        if path in ("", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if path in ("/openapi.json", "/ai_studio/openapi.json"):
            openapi_file = ROOT / "ai_studio" / "openapi.json"
            if openapi_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(openapi_file.read_bytes())
                return

        if path == "/ai_studio/tools_schema.json":
            schema_file = ROOT / "ai_studio" / "tools_schema.json"
            if schema_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(schema_file.read_bytes())
                return

        if path == "/ai_studio/system_prompt.txt":
            prompt_file = ROOT / "ai_studio" / "system_prompt.txt"
            if prompt_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(prompt_file.read_bytes())
                return

        if path == "/api/status":
            blender_found = False
            blender_path = None
            try:
                blender_path = find_blender()
                blender_found = True
            except Exception:
                pass

            data = {
                "status": "ready",
                "blender_found": blender_found,
                "blender_path": blender_path,
                "blender_version": Path(blender_path).parent.name if blender_path else "unknown",
                "python_version": sys.version.split()[0],
                "workspace": str(ROOT),
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        content_len = int(self.headers.get("Content-Length", 0))
        body_text = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req = json.loads(body_text) if body_text.strip() else {}
        except Exception as e:
            self.send_error_json(400, f"Invalid JSON body: {e}")
            return

        # Check for /api/call or /api/tool
        if path in ("/api/call", "/api/tool"):
            # Normalize Google AI Studio call formats:
            # 1. {"tool": "...", "args": {...}}
            # 2. {"name": "...", "args": {...}}
            # 3. {"functionCall": {"name": "...", "args": {...}}}
            tool = req.get("tool") or req.get("name")
            args = req.get("args", {})
            if "functionCall" in req and isinstance(req["functionCall"], dict):
                fc = req["functionCall"]
                tool = fc.get("name", tool)
                args = fc.get("args", args)

            if not tool:
                self.send_error_json(400, "Missing 'tool' or 'name' parameter in request.")
                return

            self.handle_execution(tool, args)
            return

        # Check for individual REST endpoints /api/tools/<tool_name>
        if path.startswith("/api/tools/"):
            tool_name = path[len("/api/tools/"):]
            self.handle_execution(tool_name, req)
            return

        self.send_error(404, "Not Found")

    def handle_execution(self, tool: str, args: dict):
        try:
            res = self.dispatch_tool(tool, args)
            status = 200
            payload = {
                "success": True,
                "tool": tool,
                "result": res,
                "functionResponse": {
                    "name": tool,
                    "response": {
                        "output": res
                    }
                }
            }
        except Exception as e:
            status = 500
            payload = {
                "success": False,
                "tool": tool,
                "error": str(e),
                "functionResponse": {
                    "name": tool,
                    "response": {
                        "error": str(e)
                    }
                }
            }

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def send_error_json(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

    def dispatch_tool(self, tool: str, args: dict) -> dict:
        print(f"[Bridge Request] {tool}({args})")
        if tool == "get_engine_vocabulary":
            return get_engine_vocabulary()
        elif tool == "validate_shotlist":
            return validate_shotlist(args.get("episode_path", ""))
        elif tool == "create_new_episode":
            return create_new_episode(
                args.get("episode_id", ""),
                args.get("title", ""),
                args.get("format_name", "what_if"),
                args.get("script_markdown", ""),
                args.get("shots_data", {}),
            )
        elif tool == "generate_voiceover":
            return generate_voiceover(args.get("episode_path", ""))
        elif tool == "build_blender_scene":
            return build_blender_scene(args.get("episode_path", ""))
        elif tool == "render_contact_sheet":
            return render_contact_sheet(args.get("episode_path", ""))
        elif tool == "render_video_pipeline":
            return render_video_pipeline(
                args.get("episode_path", ""),
                final=args.get("final", False),
                only_stages=args.get("only_stages"),
                from_stage=args.get("from_stage"),
            )
        elif tool == "render_thumbnail":
            return render_thumbnail(args.get("episode_path", ""))
        elif tool == "inspect_frame":
            return inspect_frame(
                args.get("episode_path", ""), int(args.get("frame_number", 0))
            )
        else:
            raise ValueError(f"Unknown tool: '{tool}'")


def run_server(port: int = 8080):
    handler = BridgeHandler
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Roblox Tools Bridge Server running at http://127.0.0.1:{port}/")
        print("Press Ctrl+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Roblox Tools Studio Bridge")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to listen on (default 8080)"
    )
    args = parser.parse_args()
    run_server(args.port)
