#!/usr/bin/env python3
"""Google AI Studio / Gemini Director Runner for Roblox Animation Pipeline.

Connects Gemini (e.g. gemini-2.5-flash or gemini-1.5-pro) directly to the local
Blender Roblox animation engine using Google GenAI SDK and Automatic Function
Calling.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit(
        "google-genai package not found. Install it with: pip install google-genai"
    )

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


# Tool wrappers with clean docstrings for Gemini
def get_engine_vocabulary_tool() -> str:
    """Retrieve the full vocabulary of the Roblox animation engine including cast presets, sets, marks, poses, faces, actions, props, sfx, and music moods.

    Call this first to know valid engine elements.
    """
    print("\n[Tool Call] -> get_engine_vocabulary()")
    res = get_engine_vocabulary()
    return json.dumps(res)


def validate_shotlist_tool(episode_path: str) -> str:
    """Validate an episode's shots.json against the engine vocabulary and camera rules.

    Args:
        episode_path: Path to the episode directory, e.g.
          'episodes/wi_zlatan_bff'.
    """
    print(f"\n[Tool Call] -> validate_shotlist({episode_path})")
    res = validate_shotlist(episode_path)
    return json.dumps(res)


def create_new_episode_tool(
    episode_id: str,
    title: str,
    format_name: str,
    script_markdown: str,
    shots_json_str: str,
) -> str:
    """Create a new episode directory with script.md and shots.json, and validate it.

    Args:
        episode_id: Slug like 'wi_golden_ball' or 'itt_fast_police'.
        title: Catchy title for the video.
        format_name: Format name ('what_if' or 'in_this_town').
        script_markdown: Markdown beat sheet with narration beats.
        shots_json_str: Valid JSON string adhering to SHOTLIST_FORMAT.md schema.
    """
    print(f"\n[Tool Call] -> create_new_episode({episode_id}, {title})")
    try:
        shots_data = json.loads(shots_json_str)
    except json.JSONDecodeError as e:
        return json.dumps(
            {"success": False, "error": f"Invalid shots_json_str: {e}"}
        )

    res = create_new_episode(
        episode_id, title, format_name, script_markdown, shots_data
    )
    return json.dumps(res)


def generate_voiceover_tool(episode_path: str) -> str:
    """Generate line-by-line speech audio and word timing JSON for the episode.

    Args:
        episode_path: Path to episode directory.
    """
    print(f"\n[Tool Call] -> generate_voiceover({episode_path})")
    res = generate_voiceover(episode_path)
    return json.dumps(res)


def build_blender_scene_tool(episode_path: str) -> str:
    """Build the 3D scene in Blender in background mode to produce <episode>.blend.

    Args:
        episode_path: Path to episode directory.
    """
    print(f"\n[Tool Call] -> build_blender_scene({episode_path})")
    res = build_blender_scene(episode_path)
    return json.dumps(res)


def render_contact_sheet_tool(episode_path: str) -> str:
    """Render a visual QA contact sheet with one labeled frame from every shot.

    Args:
        episode_path: Path to episode directory.
    """
    print(f"\n[Tool Call] -> render_contact_sheet({episode_path})")
    res = render_contact_sheet(episode_path)
    return json.dumps(res)


def render_video_pipeline_tool(
    episode_path: str, final: bool = False, only_stages: str = ""
) -> str:
    """Render the full video and VSE edit with voice, music, sfx, captions, and title card.

    Args:
        episode_path: Path to episode directory.
        final: True for final 1080x1920 with publish pack; False for preview.
        only_stages: Optional comma-separated stages (e.g. 'raw,edit').
    """
    print(
        f"\n[Tool Call] -> render_video_pipeline({episode_path}, final={final})"
    )
    res = render_video_pipeline(
        episode_path,
        final=final,
        only_stages=only_stages if only_stages else None,
    )
    return json.dumps(res)


def render_thumbnail_tool(episode_path: str) -> str:
    """Render the YouTube/TikTok thumbnail image with title card overlay.

    Args:
        episode_path: Path to episode directory.
    """
    print(f"\n[Tool Call] -> render_thumbnail({episode_path})")
    res = render_thumbnail(episode_path)
    return json.dumps(res)


def inspect_frame_tool(episode_path: str, frame_number: int) -> str:
    """Render a single frame from the episode blend file to an image for QA inspection.

    Args:
        episode_path: Path to episode directory.
        frame_number: The integer frame number to render.
    """
    print(f"\n[Tool Call] -> inspect_frame({episode_path}, frame={frame_number})")
    res = inspect_frame(episode_path, frame_number)
    return json.dumps(res)


TOOLS = [
    get_engine_vocabulary_tool,
    validate_shotlist_tool,
    create_new_episode_tool,
    generate_voiceover_tool,
    build_blender_scene_tool,
    render_contact_sheet_tool,
    render_video_pipeline_tool,
    render_thumbnail_tool,
    inspect_frame_tool,
]


def load_system_instruction() -> str:
    prompt_file = ROOT / "ai_studio" / "system_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "You are the Roblox 3D Animation Director using automated Blender tools."


def main():
    parser = argparse.ArgumentParser(
        description="Run Gemini with Roblox Animation Tools from Google AI Studio / Gemini API"
    )
    parser.add_argument("prompt", nargs="?", help="Initial user prompt / idea")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model name (default: gemini-2.5-flash)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start an interactive chat session",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Check .env
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    os.environ["GOOGLE_API_KEY"] = api_key
                    break

    if not api_key:
        sys.exit(
            "GOOGLE_API_KEY not found. Please set GOOGLE_API_KEY environment variable or in .env."
        )

    print(f"Connecting to Gemini ({args.model}) with Google GenAI SDK...")
    client = genai.Client(http_options={"api_version": "v1beta"})
    system_instruction = load_system_instruction()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=TOOLS,
        temperature=0.7,
    )

    chat = client.chats.create(model=args.model, config=config)
    print("Ready! Tools registered:")
    for t in TOOLS:
        print(f"  * {t.__name__}")
    print("-" * 60)

    if args.prompt:
        print(f"\nUser: {args.prompt}")
        resp = chat.send_message(args.prompt)
        print(f"\nGemini Director:\n{resp.text}\n")

    if args.interactive or not args.prompt:
        print("Entering interactive mode. Type 'quit' or 'exit' to stop.")
        while True:
            try:
                user_msg = input("\nYou: ").strip()
                if not user_msg:
                    continue
                if user_msg.lower() in ("quit", "exit"):
                    break
                resp = chat.send_message(user_msg)
                print(f"\nGemini Director:\n{resp.text}\n")
            except (KeyboardInterrupt, EOFError):
                break


if __name__ == "__main__":
    main()
