#!/usr/bin/env python3
"""Google AI Studio Local Bridge Server.

Provides a lightweight local web dashboard and REST API for Google AI Studio.
Allows users in Google AI Studio's web UI to easily execute function calls locally
and paste responses back into the AI Studio prompt runner.
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.roblox_tools import (
    build_blender_scene,
    create_new_episode,
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
  <title>Google AI Studio - Roblox Animation Tools Bridge</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
    .container { max-width: 900px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    h1 { margin-top: 0; color: #38bdf8; font-size: 24px; }
    p { color: #94a3b8; line-height: 1.5; }
    .badge { display: inline-block; background: #0284c7; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; }
    .card { background: #334155; padding: 16px; border-radius: 8px; border: 1px solid #475569; }
    label { font-weight: 600; display: block; margin-bottom: 6px; font-size: 14px; }
    select, input, textarea { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: #f8fafc; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 13px; margin-bottom: 12px; }
    button { background: #38bdf8; color: #0f172a; border: none; padding: 10px 18px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
    button:hover { background: #7dd3fc; }
    pre { background: #0f172a; padding: 12px; border-radius: 6px; overflow-x: auto; color: #a5f3fc; font-size: 12px; max-height: 350px; }
    .copy-btn { float: right; background: #475569; color: #fff; padding: 4px 8px; font-size: 11px; }
  </style>
</head>
<body>
  <div class="container">
    <span class="badge">Google AI Studio Local Bridge</span>
    <h1>Roblox Animation Pipeline Bridge</h1>
    <p>Execute function calls requested by Gemini in Google AI Studio and copy the function response directly back.</p>
    
    <div class="card">
      <label for="toolSelect">Select Tool:</label>
      <select id="toolSelect" onchange="updateDefaultArgs()">
        <option value="get_engine_vocabulary">get_engine_vocabulary()</option>
        <option value="validate_shotlist">validate_shotlist(episode_path)</option>
        <option value="generate_voiceover">generate_voiceover(episode_path)</option>
        <option value="build_blender_scene">build_blender_scene(episode_path)</option>
        <option value="render_contact_sheet">render_contact_sheet(episode_path)</option>
        <option value="render_video_pipeline">render_video_pipeline(episode_path, final, only_stages)</option>
        <option value="render_thumbnail">render_thumbnail(episode_path)</option>
        <option value="inspect_frame">inspect_frame(episode_path, frame_number)</option>
        <option value="create_new_episode">create_new_episode(...)</option>
      </select>

      <label for="argsInput">Arguments (JSON):</label>
      <textarea id="argsInput" rows="5">{}</textarea>

      <button onclick="executeTool()">Execute Tool</button>
      <button onclick="copySchema()" style="background:#64748b; color:#fff; margin-left:8px;">Copy Tools Schema for AI Studio</button>
    </div>

    <div class="card" style="margin-top: 20px;">
      <button class="copy-btn" onclick="copyResult()">Copy Result</button>
      <label>Execution Output:</label>
      <pre id="outputBox">// Tool execution results will appear here...</pre>
    </div>
  </div>

  <script>
    const sampleArgs = {
      "get_engine_vocabulary": "{}",
      "validate_shotlist": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "generate_voiceover": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "build_blender_scene": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "render_contact_sheet": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "render_video_pipeline": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff", "final": false}, null, 2),
      "render_thumbnail": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff"}, null, 2),
      "inspect_frame": JSON.stringify({"episode_path": "episodes/wi_zlatan_bff", "frame_number": 30}, null, 2),
      "create_new_episode": JSON.stringify({
        "episode_id": "wi_demo",
        "title": "What If Roblox Characters Won The Cup?",
        "format_name": "what_if",
        "script_markdown": "# Script",
        "shots_data": {}
      }, null, 2)
    };

    function updateDefaultArgs() {
      const tool = document.getElementById("toolSelect").value;
      document.getElementById("argsInput").value = sampleArgs[tool] || "{}";
    }

    async function executeTool() {
      const tool = document.getElementById("toolSelect").value;
      const argsStr = document.getElementById("argsInput").value;
      let argsObj = {};
      try {
        argsObj = JSON.parse(argsStr);
      } catch(e) {
        alert("Invalid JSON arguments: " + e);
        return;
      }

      document.getElementById("outputBox").innerText = "Executing " + tool + "...";
      try {
        const resp = await fetch("/api/tool", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({tool: tool, args: argsObj})
        });
        const resJson = await resp.json();
        document.getElementById("outputBox").innerText = JSON.stringify(resJson, null, 2);
      } catch(err) {
        document.getElementById("outputBox").innerText = "Error: " + err;
      }
    }

    function copyResult() {
      const text = document.getElementById("outputBox").innerText;
      navigator.clipboard.writeText(text);
      alert("Result copied to clipboard! Paste it into Google AI Studio as the function response.");
    }

    async function copySchema() {
      const resp = await fetch("/ai_studio/tools_schema.json");
      const jsonText = await resp.text();
      navigator.clipboard.writeText(jsonText);
      alert("AI Studio Tools Schema copied to clipboard!");
    }
  </script>
</body>
</html>
"""


class BridgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        elif url.path == "/ai_studio/tools_schema.json":
            schema_file = ROOT / "ai_studio" / "tools_schema.json"
            if schema_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(schema_file.read_bytes())
                return
        super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/tool":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                req = json.loads(body)
                tool = req.get("tool")
                args = req.get("args", {})
                result = self.dispatch_tool(tool, args)
                status = 200
            except Exception as e:
                result = {"error": str(e)}
                status = 400

            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode("utf-8"))
            return

        self.send_error(404, "Not Found")

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
            raise ValueError(f"Unknown tool: {tool}")


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
