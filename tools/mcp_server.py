"""FastMCP Server for the Blender Roblox Animation Pipeline.

Allows Claude, Cursor, Antigravity, and any MCP client to query engine
vocabulary, create episodes, validate shotlists, synthesize voiceovers, build
scenes, and render videos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP
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

mcp = FastMCP("roblox-animation-engine")


@mcp.tool()
def get_vocabulary() -> Dict[str, Any]:
    """Retrieve the strict engine vocabulary: available cast presets, sets, dressings, marks, poses, faces, actions, props, sfx, and music moods.

    Always call this before authoring a script or shotlist!
    """
    return get_engine_vocabulary()


@mcp.tool()
def validate_episode(episode_path: str) -> Dict[str, Any]:
    """Validate an episode's shots.json against engine vocabulary and camera/directing rules.

    Args:
        episode_path: Path to the episode folder (e.g. 'episodes/wi_zlatan_bff').
    """
    return validate_shotlist(episode_path)


@mcp.tool()
def create_episode(
    episode_id: str,
    title: str,
    format_name: str,
    script_markdown: str,
    shots_json_content: str,
) -> Dict[str, Any]:
    """Create a new episode directory with script.md and shots.json, then validate it.

    Args:
        episode_id: Unique slug prefixed with 'wi_' (what if) or 'itt_' (in this
          town), e.g. 'wi_zlatan_magic'.
        title: Title of the short.
        format_name: Format name ('what_if' or 'in_this_town').
        script_markdown: The markdown beat sheet / script.
        shots_json_content: JSON string representing the full shots.json
          specification.
    """
    data = json.loads(shots_json_content)
    return create_new_episode(
        episode_id, title, format_name, script_markdown, data
    )


@mcp.tool()
def voiceover(episode_path: str) -> Dict[str, Any]:
    """Synthesize voiceovers for all dialogue shots and produce timing.json with word-level alignment timestamps.

    Args:
        episode_path: Path to the episode directory.
    """
    return generate_voiceover(episode_path)


@mcp.tool()
def build_scene(episode_path: str) -> Dict[str, Any]:
    """Execute headless Blender to assemble sets, characters, props, animations, and cameras into <episode>.blend.

    Args:
        episode_path: Path to the episode directory.
    """
    return build_blender_scene(episode_path)


@mcp.tool()
def contact_sheet(episode_path: str) -> Dict[str, Any]:
    """Render a labeled contact sheet containing stills from the middle of every shot for quick visual QA.

    Args:
        episode_path: Path to the episode directory.
    """
    return render_contact_sheet(episode_path)


@mcp.tool()
def render_pipeline(
    episode_path: str,
    final: bool = False,
    only_stages: Optional[str] = None,
    from_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the video render and editing pipeline (preview or 1080x1920 final with captions, audio mix, and publishing bundle).

    Args:
        episode_path: Path to the episode directory.
        final: If True, renders full resolution final with publishing package.
          Default is preview.
        only_stages: Comma-separated list of stages to run (e.g. 'raw,edit').
        from_stage: Stage to resume from (e.g. 'raw').
    """
    return render_video_pipeline(
        episode_path,
        final=final,
        only_stages=only_stages,
        from_stage=from_stage,
    )


@mcp.tool()
def thumbnail(episode_path: str) -> Dict[str, Any]:
    """Render the high-impact episode thumbnail with hook title card.

    Args:
        episode_path: Path to the episode directory.
    """
    return render_thumbnail(episode_path)


@mcp.tool()
def check_frame(
    episode_path: str, frame_number: int, out_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Render an individual frame from the episode blend file to inspect poses, staging, or props.

    Args:
        episode_path: Path to the episode directory.
        frame_number: The specific frame number to render.
        out_dir: Optional custom output directory.
    """
    return inspect_frame(episode_path, frame_number, out_dir=out_dir)


if __name__ == "__main__":
    mcp.run()
