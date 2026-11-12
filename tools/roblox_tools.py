"""Roblox Animation Engine Tools

Comprehensive API and CLI for programmatic execution of the Blender Roblox
Shorts Animation Pipeline.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"

# Load .env if present
_env_file = ROOT / ".env"
if _env_file.exists():
    try:
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v
    except Exception:
        pass


def find_blender() -> str:
    """Locate the Blender executable across Windows, macOS, Linux, or env vars."""
    if os.environ.get("BLENDER"):
        cand = os.environ["BLENDER"]
        if Path(cand).exists():
            return cand

    # Standard Windows install locations
    win_patterns = [
        r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
        r"C:\Program Files (x86)\Blender Foundation\Blender *\blender.exe",
        r"C:\Program Files\Steam\steamapps\common\Blender\blender.exe",
        r"D:\SteamLibrary\steamapps\common\Blender\blender.exe",
        r"D:\Program Files\Blender Foundation\Blender *\blender.exe",
    ]
    for pat in win_patterns:
        found = sorted(
            glob.glob(pat),
            key=lambda p: [
                int(x) if x.isdigit() else x
                for x in Path(p).parent.name.split()[-1].split(".")
            ],
        )
        if found:
            return found[-1]

    # macOS application bundle
    mac_app = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac_app.exists():
        return str(mac_app)

    # Linux standard paths
    for lin in ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]:
        if Path(lin).exists():
            return lin

    # Fallback to system PATH
    which = shutil.which("blender")
    if which:
        return which

    raise FileNotFoundError(
        "Blender not found. Install Blender 5.x or set BLENDER env variable."
    )


def get_engine_vocabulary() -> Dict[str, Any]:
    """Return the engine's strict vocabulary as a structured dictionary.

    Includes cast, sets, dressing, marks, poses, faces, actions, props, sfx, and music moods.
    """
    sys.path.insert(0, str(PIPE))
    try:
        import vocab

        c = vocab.catalog()
        sets_dict: Dict[str, Any] = {}
        for sname, sdef in c.get("sets", {}).items():
            sets_dict[sname] = {
                "dressings": sdef.get("dressings", []),
                "marks": sdef.get("marks", {}),
            }

        cast_list = []
        for name in c.get("characters", []):
            cast_list.append({
                "name": name,
                "notes": vocab.CAST_NOTES.get(name, ""),
            })

        return {
            "cast": cast_list,
            "custom_character_options": {
                "hair_styles": vocab.HAIR_STYLES,
                "hats": vocab.HATS,
                "extras": vocab.EXTRAS,
                "details": vocab.DETAILS,
                "sleeves": vocab.SLEEVES,
                "bottoms": vocab.BOTTOMS,
            },
            "sets": sets_dict,
            "poses": vocab.POSES,
            "faces": vocab.FACES,
            "actions": vocab.ACTIONS,
            "props": vocab.PROPS,
            "sfx": vocab.sfx_names(),
            "music": vocab.music_moods(),
            "formats": vocab.formats(),
            "camera": {
                "shots": vocab.CAMERA_SHOTS,
                "angles": vocab.CAMERA_ANGLES,
                "moves": vocab.CAMERA_MOVES,
            },
            "facings": vocab.FACINGS,
            "transitions": vocab.TRANSITIONS,
            "fx": vocab.FX,
            "place_keys": vocab.PLACE_KEYS,
        }
    finally:
        if str(PIPE) in sys.path:
            sys.path.remove(str(PIPE))


def validate_shotlist(episode_path: str) -> Dict[str, Any]:
    """Validate an episode's shots.json against engine vocabulary and rules.

    Returns dict with valid status, error messages, and warnings.
    """
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep
    shots_file = ep / "shots.json"
    if not shots_file.exists():
        return {
            "valid": False,
            "errors": [f"File not found: {shots_file}"],
            "warnings": [],
        }

    cmd = [sys.executable, str(PIPE / "validate.py"), str(ep)]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    output = (p.stdout + "\n" + p.stderr).strip()

    errors = []
    warnings = []
    for line in output.splitlines():
        line = line.strip()
        if "ERROR" in line or line.startswith("!"):
            errors.append(line)
        elif "WARN" in line:
            warnings.append(line)

    valid = p.returncode == 0 and len(errors) == 0
    return {
        "valid": valid,
        "returncode": p.returncode,
        "errors": errors,
        "warnings": warnings,
        "raw_output": output,
    }


def create_new_episode(
    episode_id: str,
    title: str,
    format_name: str,
    script_markdown: str,
    shots_data: Dict[str, Any] | str,
) -> Dict[str, Any]:
    """Create a new episode folder with script.md and shots.json, then validate it."""
    if not episode_id or not str(episode_id).strip():
        return {
            "success": False,
            "error": "episode_id is required and cannot be empty.",
            "validation": {"valid": False, "errors": ["episode_id cannot be empty"], "warnings": []},
        }

    episode_id = str(episode_id).strip()
    if isinstance(shots_data, str):
        try:
            shots_data = json.loads(shots_data)
        except Exception as e:
            return {
                "success": False,
                "episode_id": episode_id,
                "error": f"Invalid shots_data JSON string: {e}",
                "validation": {"valid": False, "errors": [f"shots_data parse error: {e}"], "warnings": []},
            }

    if not isinstance(shots_data, dict):
        shots_data = {}

    ep_dir = ROOT / "episodes" / episode_id
    ep_dir.mkdir(parents=True, exist_ok=True)

    # Ensure metadata matches
    shots_data["episode"] = episode_id
    shots_data["title"] = title
    shots_data["format"] = format_name

    script_path = ep_dir / "script.md"
    script_path.write_text(script_markdown, encoding="utf-8")

    shots_path = ep_dir / "shots.json"
    shots_path.write_text(json.dumps(shots_data, indent=2), encoding="utf-8")

    val = validate_shotlist(str(ep_dir))
    return {
        "success": True,
        "episode_id": episode_id,
        "episode_dir": str(ep_dir),
        "validation": val,
    }


def generate_voiceover(episode_path: str) -> Dict[str, Any]:
    """Generate audio files and timing.json for the episode.

    Uses ElevenLabs (if ELEVENLABS_API_KEY is configured in .env) or Edge TTS fallback.
    """
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep
    cmd = [sys.executable, str(PIPE / "voiceover.py"), str(ep)]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    timing_file = ep / "timing.json"

    if p.returncode != 0 or not timing_file.exists():
        return {
            "success": False,
            "error": p.stderr or p.stdout,
            "timing_file": None,
        }

    timing_data = json.loads(timing_file.read_text(encoding="utf-8"))
    return {
        "success": True,
        "timing_file": str(timing_file),
        "total_duration": timing_data.get("total_duration", 0.0),
        "shot_count": len(timing_data.get("shots", [])),
    }


def build_blender_scene(episode_path: str) -> Dict[str, Any]:
    """Build the 3D Blender scene (<episode>.blend) with sets, rigs, cameras, and animation."""
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep

    blender = find_blender()
    logs_dir = ep / "render" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    build_log = logs_dir / "build.log"

    cmd = [
        blender,
        "-b",
        "--factory-startup",
        "--python",
        str(PIPE / "episode.py"),
        "--",
        str(ep),
    ]

    with open(build_log, "w", encoding="utf-8", errors="replace") as fh:
        p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)

    text = build_log.read_text(encoding="utf-8", errors="replace")
    success = p.returncode == 0 and "BUILT" in text and "Traceback" not in text

    shots_file = ep / "shots.json"
    blend_slug = ep.name
    if shots_file.exists():
        try:
            sd = json.loads(shots_file.read_text(encoding="utf-8"))
            blend_slug = sd.get("episode", ep.name)
        except Exception:
            pass
    blend_file = ep / f"{blend_slug}.blend"

    return {
        "success": success,
        "blend_file": str(blend_file) if blend_file.exists() else None,
        "log_file": str(build_log),
        "log_tail": "\n".join(text.splitlines()[-25:]),
    }


def render_contact_sheet(episode_path: str) -> Dict[str, Any]:
    """Render a contact sheet of labeled stills from the middle of each shot for quick QA."""
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep

    cmd = [sys.executable, str(PIPE / "make.py"), str(ep), "--only", "sheet"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    sheet_img = ep / "render" / "contact_sheet.png"

    return {
        "success": sheet_img.exists(),
        "contact_sheet_path": str(sheet_img) if sheet_img.exists() else None,
        "output": p.stdout,
        "error": p.stderr if p.returncode != 0 else None,
    }


def render_video_pipeline(
    episode_path: str,
    final: bool = False,
    only_stages: Optional[str] = None,
    from_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the complete animation pipeline or resume from a specific stage."""
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep

    cmd = [sys.executable, str(PIPE / "make.py"), str(ep)]
    if final:
        cmd.append("--final")
    if only_stages:
        cmd.extend(["--only", only_stages])
    if from_stage:
        cmd.extend(["--from", from_stage])

    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    elapsed = time.time() - t0

    q = "final" if final else "preview"
    outs = sorted((ep / "out").glob(f"*_{q}.mp4")) if (ep / "out").exists() else []

    shots_file = ep / "shots.json"
    blend_slug = ep.name
    if shots_file.exists():
        try:
            sd = json.loads(shots_file.read_text(encoding="utf-8"))
            blend_slug = sd.get("episode", ep.name)
        except Exception:
            pass
    publish_dir = ROOT / "publish" / blend_slug
    if not publish_dir.exists():
        publish_dir = ROOT / "publish" / ep.name

    return {
        "success": p.returncode == 0,
        "elapsed_seconds": round(elapsed, 1),
        "quality": q,
        "output_videos": [str(o) for o in outs],
        "publish_files": (
            [str(f) for f in publish_dir.iterdir()]
            if publish_dir.exists()
            else []
        ),
        "stdout": p.stdout[-2000:] if p.stdout else "",
        "stderr": p.stderr[-1000:] if p.stderr else "",
    }


def render_thumbnail(episode_path: str) -> Dict[str, Any]:
    """Generate the branded thumbnail with hook title card."""
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep

    cmd = [sys.executable, str(PIPE / "make.py"), str(ep), "--only", "thumb"]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    thumb_img = ep / "out" / "thumbnail.png"
    return {
        "success": thumb_img.exists(),
        "thumbnail_path": str(thumb_img) if thumb_img.exists() else None,
        "output": p.stdout,
        "error": p.stderr if p.returncode != 0 else None,
    }


def inspect_frame(episode_path: str, frame_number: int, out_dir: Optional[str] = None) -> Dict[str, Any]:
    """Render a specific frame from the episode blend file for visual QA."""
    ep = Path(episode_path)
    if not ep.is_absolute():
        ep = ROOT / ep

    shots_file = ep / "shots.json"
    blend_slug = ep.name
    if shots_file.exists():
        try:
            sd = json.loads(shots_file.read_text(encoding="utf-8"))
            blend_slug = sd.get("episode", ep.name)
        except Exception:
            pass

    blend_file = ep / f"{blend_slug}.blend"
    if not blend_file.exists():
        blend_file = ep / f"{ep.name}.blend"

    if not blend_file.exists():
        return {
            "success": False,
            "error": f"Blend file not found: {blend_file}. Run build first.",
        }

    target_dir = Path(out_dir) if out_dir else ep / "render" / "inspect"
    target_dir.mkdir(parents=True, exist_ok=True)

    frame_num = int(frame_number)
    blender = find_blender()
    cmd = [
        blender,
        "-b",
        str(blend_file),
        "--python",
        str(PIPE / "frames.py"),
        "--",
        str(target_dir),
        str(frame_num),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)

    # frames.py renders to f{frame:05d}.png
    primary_png = target_dir / f"f{frame_num:05d}.png"
    secondary_png = target_dir / f"frame_{frame_num:05d}.png"

    frame_png = None
    if primary_png.exists():
        frame_png = primary_png
    elif secondary_png.exists():
        frame_png = secondary_png
    else:
        # Fallback to exact match on formatted frame number only
        matches = list(target_dir.glob(f"*{frame_num:05d}*.png"))
        if matches:
            frame_png = matches[0]

    return {
        "success": frame_png is not None and frame_png.exists(),
        "frame_image": str(frame_png) if frame_png and frame_png.exists() else None,
        "stdout": p.stdout[-1000:] if p.stdout else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Roblox Shorts Automation Tools CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # vocab
    subparsers.add_parser("vocab", help="Output engine vocabulary JSON")

    # validate
    val_p = subparsers.add_parser("validate", help="Validate an episode shotlist")
    val_p.add_argument("episode", help="Path to episode folder (e.g. episodes/wi_zlatan_bff)")

    # voice
    voice_p = subparsers.add_parser("voice", help="Generate voiceovers and timing.json")
    voice_p.add_argument("episode", help="Path to episode folder")

    # build
    build_p = subparsers.add_parser("build", help="Build Blender .blend scene")
    build_p.add_argument("episode", help="Path to episode folder")

    # sheet
    sheet_p = subparsers.add_parser("sheet", help="Render contact sheet for visual QA")
    sheet_p.add_argument("episode", help="Path to episode folder")

    # render
    render_p = subparsers.add_parser("render", help="Run full render pipeline")
    render_p.add_argument("episode", help="Path to episode folder")
    render_p.add_argument("--final", action="store_true", help="Render in final 1080x1920 quality")
    render_p.add_argument("--only", help="Comma-separated stages to run")
    render_p.add_argument("--from-stage", help="Resume from this stage")

    # thumb
    thumb_p = subparsers.add_parser("thumb", help="Render thumbnail")
    thumb_p.add_argument("episode", help="Path to episode folder")

    # frame
    frame_p = subparsers.add_parser("frame", help="Inspect a specific frame")
    frame_p.add_argument("episode", help="Path to episode folder")
    frame_p.add_argument("frame_number", type=int, help="Frame number to render")

    args = parser.parse_args()

    if args.command == "vocab":
        print(json.dumps(get_engine_vocabulary(), indent=2))
    elif args.command == "validate":
        res = validate_shotlist(args.episode)
        print(json.dumps(res, indent=2))
    elif args.command == "voice":
        res = generate_voiceover(args.episode)
        print(json.dumps(res, indent=2))
    elif args.command == "build":
        res = build_blender_scene(args.episode)
        print(json.dumps(res, indent=2))
    elif args.command == "sheet":
        res = render_contact_sheet(args.episode)
        print(json.dumps(res, indent=2))
    elif args.command == "render":
        res = render_video_pipeline(
            args.episode,
            final=args.final,
            only_stages=args.only,
            from_stage=args.from_stage,
        )
        print(json.dumps(res, indent=2))
    elif args.command == "thumb":
        res = render_thumbnail(args.episode)
        print(json.dumps(res, indent=2))
    elif args.command == "frame":
        res = inspect_frame(args.episode, args.frame_number)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
