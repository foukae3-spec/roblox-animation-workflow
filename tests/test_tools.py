"""Comprehensive Automated Test Suite for Roblox Animation Engine & Google AI Studio Tools."""

import json
import shutil
import sys
import unittest
from pathlib import Path

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
from ai_studio.studio_bridge_server import BridgeHandler
from ai_studio import gemini_director


class TestRobloxTools(unittest.TestCase):
    def test_01_engine_vocabulary(self):
        """Test that get_engine_vocabulary returns all required structural elements."""
        vocab = get_engine_vocabulary()
        self.assertIsInstance(vocab, dict)
        required_keys = [
            "cast", "sets", "poses", "faces", "actions", "props",
            "sfx", "music", "formats", "camera", "facings", "transitions", "fx", "place_keys"
        ]
        for key in required_keys:
            self.assertIn(key, vocab, f"Missing vocabulary key: {key}")

        # Check cast presets
        cast_names = [c["name"] for c in vocab["cast"]]
        self.assertIn("Theo", cast_names)
        self.assertIn("Zlatan", cast_names)
        self.assertIn("Noob", cast_names)
        self.assertIn("King", cast_names)

        # Check sets
        self.assertIn("bedroom", vocab["sets"])
        self.assertIn("classroom", vocab["sets"])
        self.assertIn("street", vocab["sets"])

        # Check camera options
        self.assertIn("close_up", vocab["camera"]["shots"])
        self.assertIn("crash_zoom", vocab["camera"]["moves"])

    def test_02_validate_shotlist_valid(self):
        """Test validation on the real sample episode wi_zlatan_bff."""
        res = validate_shotlist("episodes/wi_zlatan_bff")
        self.assertTrue(res["valid"])
        self.assertEqual(res["returncode"], 0)
        self.assertEqual(len(res["errors"]), 0)

    def test_03_validate_shotlist_missing_folder(self):
        """Test validation error handling on non-existent episode path."""
        res = validate_shotlist("episodes/non_existent_folder_xyz")
        self.assertFalse(res["valid"])
        self.assertTrue(any("not found" in err.lower() for err in res["errors"]))

    def test_04_create_new_episode_dict(self):
        """Test episode creation when shots_data is passed as a dict."""
        ep_id = "wi_test_tmp_dict"
        ep_dir = ROOT / "episodes" / ep_id
        if ep_dir.exists():
            shutil.rmtree(ep_dir, ignore_errors=True)

        try:
            shots_spec = {
                "episode": ep_id,
                "title": "Test Title",
                "format": "what_if",
                "shots": [
                    {
                        "id": "s1",
                        "set": "bedroom",
                        "speaker": "narrator",
                        "text": "What if Zlatan won?",
                        "camera": {"shot": "medium", "angle": "eye", "move": "static"},
                        "cast": [{"name": "Theo", "mark": "center", "action": "talk"}]
                    }
                ]
            }
            res = create_new_episode(
                episode_id=ep_id,
                title="Test Title",
                format_name="what_if",
                script_markdown="# Test Script",
                shots_data=shots_spec,
            )
            self.assertTrue(res["success"])
            self.assertTrue(ep_dir.exists())
            self.assertTrue((ep_dir / "script.md").exists())
            self.assertTrue((ep_dir / "shots.json").exists())

            # Read shots.json and confirm content
            saved_shots = json.loads((ep_dir / "shots.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_shots["episode"], ep_id)
            self.assertEqual(saved_shots["title"], "Test Title")
        finally:
            if ep_dir.exists():
                shutil.rmtree(ep_dir, ignore_errors=True)

    def test_05_create_new_episode_json_string(self):
        """Test episode creation when shots_data is passed as a JSON string."""
        ep_id = "wi_test_tmp_str"
        ep_dir = ROOT / "episodes" / ep_id
        if ep_dir.exists():
            shutil.rmtree(ep_dir, ignore_errors=True)

        try:
            shots_spec_str = json.dumps({
                "episode": ep_id,
                "title": "String Test",
                "format": "what_if",
                "shots": [
                    {
                        "id": "s1",
                        "set": "classroom",
                        "speaker": "narrator",
                        "text": "Hello world from string test",
                        "camera": {"shot": "wide", "angle": "eye", "move": "static"},
                        "cast": [{"name": "Noob", "mark": "center", "action": "idle"}]
                    }
                ]
            })
            res = create_new_episode(
                episode_id=ep_id,
                title="String Test",
                format_name="what_if",
                script_markdown="# String Script",
                shots_data=shots_spec_str,
            )
            self.assertTrue(res["success"])
            self.assertTrue(ep_dir.exists())
            self.assertTrue((ep_dir / "shots.json").exists())
        finally:
            if ep_dir.exists():
                shutil.rmtree(ep_dir, ignore_errors=True)

    def test_06_create_new_episode_invalid_inputs(self):
        """Test error handling on invalid JSON string or empty episode_id."""
        # Empty episode_id
        res_empty = create_new_episode("", "Title", "what_if", "#", {})
        self.assertFalse(res_empty["success"])
        self.assertIn("error", res_empty)

        # Invalid JSON string
        res_bad_json = create_new_episode("wi_bad", "Title", "what_if", "#", "NOT_JSON{")
        self.assertFalse(res_bad_json["success"])
        self.assertIn("Invalid shots_data", res_bad_json["error"])

    def test_07_find_blender(self):
        """Test blender discovery on local system."""
        b_path = find_blender()
        self.assertIsNotNone(b_path)
        self.assertTrue(Path(b_path).exists(), f"Blender executable not found at: {b_path}")

    def test_08_inspect_frame_resolution(self):
        """Test inspect_frame resolves existing rendered frames properly."""
        # Frame 30 was rendered in wi_zlatan_bff
        res = inspect_frame("episodes/wi_zlatan_bff", 30)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["frame_image"])
        self.assertTrue(Path(res["frame_image"]).exists())
        # Confirm it ended with f00030.png
        self.assertTrue(res["frame_image"].endswith("f00030.png") or res["frame_image"].endswith("00030.png"))

    def test_09_tools_schema_json(self):
        """Validate ai_studio/tools_schema.json format and contents."""
        schema_file = ROOT / "ai_studio" / "tools_schema.json"
        self.assertTrue(schema_file.exists())
        data = json.loads(schema_file.read_text(encoding="utf-8"))
        self.assertIn("function_declarations", data)
        funcs = {fn["name"]: fn for fn in data["function_declarations"]}

        expected_tools = [
            "get_engine_vocabulary",
            "validate_shotlist",
            "create_new_episode",
            "generate_voiceover",
            "build_blender_scene",
            "render_contact_sheet",
            "render_video_pipeline",
            "render_thumbnail",
            "inspect_frame",
        ]
        for t in expected_tools:
            self.assertIn(t, funcs, f"Tool {t} missing in tools_schema.json")

    def test_10_openapi_json(self):
        """Validate ai_studio/openapi.json structure and paths."""
        openapi_file = ROOT / "ai_studio" / "openapi.json"
        self.assertTrue(openapi_file.exists())
        spec = json.loads(openapi_file.read_text(encoding="utf-8"))
        self.assertEqual(spec.get("openapi"), "3.0.3")
        self.assertIn("paths", spec)

        expected_paths = [
            "/api/tools/get_engine_vocabulary",
            "/api/tools/validate_shotlist",
            "/api/tools/create_new_episode",
            "/api/tools/generate_voiceover",
            "/api/tools/build_blender_scene",
            "/api/tools/render_contact_sheet",
            "/api/tools/render_video_pipeline",
            "/api/tools/render_thumbnail",
            "/api/tools/inspect_frame",
        ]
        for p in expected_paths:
            self.assertIn(p, spec["paths"], f"OpenAPI path {p} missing")
            self.assertIn("post", spec["paths"][p])

    def test_11_bridge_handler_dispatch(self):
        """Test BridgeHandler dispatch_tool logic."""
        handler = BridgeHandler
        # Test vocabulary
        vocab = handler.dispatch_tool(None, "get_engine_vocabulary", {})
        self.assertIsInstance(vocab, dict)
        self.assertIn("cast", vocab)

        # Test validation
        val = handler.dispatch_tool(None, "validate_shotlist", {"episode_path": "episodes/wi_zlatan_bff"})
        self.assertTrue(val["valid"])

        # Test unknown tool throws ValueError
        with self.assertRaises(ValueError):
            handler.dispatch_tool(None, "non_existent_fake_tool", {})

    def test_12_gemini_director_tool_definitions(self):
        """Test gemini_director tool signatures and tools array."""
        self.assertEqual(len(gemini_director.TOOLS), 9)

        # Test get_engine_vocabulary_tool
        vocab_json = gemini_director.get_engine_vocabulary_tool()
        self.assertIsInstance(vocab_json, str)
        vocab_data = json.loads(vocab_json)
        self.assertIn("cast", vocab_data)

        # Test validate_shotlist_tool
        val_json = gemini_director.validate_shotlist_tool("episodes/wi_zlatan_bff")
        val_data = json.loads(val_json)
        self.assertTrue(val_data["valid"])

    def test_13_bridge_server_http(self):
        """Test the bridge server HTTP endpoints and CORS behavior."""
        import socketserver
        import threading
        import urllib.request

        # Bind to port 0 (ephemeral port)
        with socketserver.TCPServer(("127.0.0.1", 0), BridgeHandler) as httpd:
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            base_url = f"http://127.0.0.1:{port}"

            # 1. GET /
            req = urllib.request.urlopen(f"{base_url}/")
            self.assertEqual(req.status, 200)
            self.assertIn("text/html", req.headers.get("Content-Type", ""))
            self.assertEqual(req.headers.get("Access-Control-Allow-Origin"), "*")

            # 2. GET /openapi.json
            req_open = urllib.request.urlopen(f"{base_url}/openapi.json")
            self.assertEqual(req_open.status, 200)
            spec = json.loads(req_open.read())
            self.assertEqual(spec.get("openapi"), "3.0.3")

            # 3. GET /api/status
            req_stat = urllib.request.urlopen(f"{base_url}/api/status")
            self.assertEqual(req_stat.status, 200)
            stat = json.loads(req_stat.read())
            self.assertEqual(stat.get("status"), "ready")

            # 4. POST /api/call with Google AI Studio functionCall payload
            post_data = json.dumps({
                "functionCall": {
                    "name": "validate_shotlist",
                    "args": {"episode_path": "episodes/wi_zlatan_bff"}
                }
            }).encode("utf-8")
            post_req = urllib.request.Request(
                f"{base_url}/api/call",
                data=post_data,
                headers={"Content-Type": "application/json"}
            )
            res_post = urllib.request.urlopen(post_req)
            self.assertEqual(res_post.status, 200)
            res_json = json.loads(res_post.read())
            self.assertTrue(res_json["success"])
            self.assertIn("functionResponse", res_json)
            self.assertEqual(res_json["functionResponse"]["name"], "validate_shotlist")

            # 5. POST /api/tools/get_engine_vocabulary (REST route)
            rest_req = urllib.request.Request(
                f"{base_url}/api/tools/get_engine_vocabulary",
                data=b"{}",
                headers={"Content-Type": "application/json"}
            )
            res_rest = urllib.request.urlopen(rest_req)
            self.assertEqual(res_rest.status, 200)
            rest_json = json.loads(res_rest.read())
            self.assertTrue(rest_json["success"])
            self.assertIn("cast", rest_json["result"])

            httpd.shutdown()


if __name__ == "__main__":
    unittest.main()
