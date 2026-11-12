# 🎬 Roblox 3D Shorts Animation Engine & Workflow

[![Blender 5.x](https://img.shields.io/badge/Blender-5.1%2B-orange?logo=blender)](https://www.blender.org/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Google AI Studio](https://img.shields.io/badge/Google%20AI%20Studio-Gemini%202.5%20%2F%201.5-8E75C4?logo=google)](https://aistudio.google.com/)
[![MCP Protocol](https://img.shields.io/badge/Model%20Context%20Protocol-FastMCP-green)](https://modelcontextprotocol.io/)

An end-to-end, code-driven 3D animation engine built on **Blender 5.x** that turns natural language video ideas into viral vertical shorts (1080×1920) featuring Roblox R6 characters.

No manual keyframing. No CapCut. Everything—from script writing and voice acting to 3D staging, camera directing, lip-syncing, sound design, auto-captions, and metadata packaging—is executed programmatically or directed by **Google AI Studio** / **Gemini**.

---

## 🌟 Highlights

- **Automated 3D Directing**: Headless Blender pipeline builds 3D sets, rigs R6 avatars, animates dynamic cameras, applies lip-sync gestures, and renders complete scenes.
- **Google AI Studio Integration**: Full support for Google AI Studio with Function Calling schemas, custom System Instructions, and an automated Gemini Director agent (`ai_studio/gemini_director.py`).
- **MCP Server Included**: Model Context Protocol (`FastMCP`) server for native integration with Claude, Cursor, and Antigravity agents.
- **Rich Asset Library**: 10 prebuilt cast members (including **Theo**, **Zlatan**, **King**, **Noob**, **Officer**), 58 hand/world props, customizable modular clothing/hair/hats, and sound effects.
- **Full VSE Post-Production**: Automatic word-synchronized karaoke captions, hook title cards, sound effects, background music moods, and social publish bundles (TikTok & YouTube Shorts).

---

## 🏗️ Pipeline Overview

```
                        ┌───────────────────────────────┐
                        │   Video Concept / Idea Prompt │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │  Google AI Studio / Gemini    │
                        │    (Queries Vocab & Tools)    │
                        └───────────────┬───────────────┘
                                        │
            ┌───────────────────────────┴───────────────────────────┐
            ▼                                                       ▼
   [ script.md + shots.json ]                              [ Audio & Timing ]
   Directing beat sheet & shot list                    ElevenLabs / Edge TTS voiceover
            │                                                       │
            └───────────────────────────┬───────────────────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    Blender 3D Scene Assembly  │
                        │   (Sets, Rigs, Props, Cameras)│
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    Visual QA Contact Sheet    │
                        │   (render/contact_sheet.png)  │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    Blender 3D Render & VSE    │
                        │ (Captions, SFX, Music, Title) │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │       Publishing Package      │
                        │  publish/<ep>/ (<ep>_final.mp4│
                        │   thumbnail.png, tiktok.txt)  │
                        └───────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Requirements
- **Python**: 3.11 or newer.
- **Blender**: Blender 5.1 or newer installed (e.g. `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`).
- **Dependencies**: Install required Python packages:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Environment Configuration
Copy `.env.example` to `.env` and set your API keys:
```env
# Google AI Studio / Gemini API Key (Required for AI Studio tools)
GOOGLE_API_KEY=AIzaSy...

# Optional: ElevenLabs for hyper-realistic voices (falls back to free Edge TTS if unset)
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional: Explicit Blender executable path if not in standard Program Files
BLENDER=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe
```

---

## 🤖 Using Tools Inside Google AI Studio

This repository is designed from the ground up to be driven by **Google AI Studio** and **Gemini 2.5 / 1.5**.

Detailed instructions are available in [`ai_studio/STUDIO_GUIDE.md`](ai_studio/STUDIO_GUIDE.md).

### Method A: Automated Gemini Director Agent (Recommended)
Run Gemini as your autonomous showrunner with one terminal command:
```bash
# Single prompt execution
python ai_studio/gemini_director.py "What if Zlatan challenged Theo to a soccer shootout?"

# Interactive directing mode
python ai_studio/gemini_director.py --interactive
```
Gemini will query the engine vocabulary, draft the episode, validate the shot list, synthesize speech, assemble the Blender scene, generate QA contact sheets, and render the final short.

### Method B: Google AI Studio Web Interface (1-Click OpenAPI Import or Tools Schema)
1. Open [Google AI Studio](https://aistudio.google.com/) and create a new **Chat Prompt**.
2. Select **Gemini 2.5 Flash** or **Gemini 1.5 Pro**.
3. Paste the contents of [`ai_studio/system_prompt.txt`](ai_studio/system_prompt.txt) into the **System Instructions** field.
4. Launch the local bridge dashboard:
   ```bash
   python ai_studio/studio_bridge_server.py --port 8080
   ```
5. In Google AI Studio under **Tools** -> **Function Calling**:
   - **Option 1 (1-Click OpenAPI)**: Click **Import OpenAPI spec** and paste [`ai_studio/openapi.json`](ai_studio/openapi.json) (or enter `http://127.0.0.1:8080/openapi.json`).
   - **Option 2 (JSON Schema)**: Copy function declarations from [`ai_studio/tools_schema.json`](ai_studio/tools_schema.json).
6. Open `http://localhost:8080` in your browser. Whenever Gemini requests a tool, paste the tool call, click **Execute**, and copy the formatted `functionResponse` back into Google AI Studio.

---

## 🔌 Using with Claude / MCP (Model Context Protocol)

An MCP server is included in `tools/mcp_server.py`.

### Configuration in `.mcp.json`
```json
{
  "mcpServers": {
    "roblox-animation": {
      "command": "python",
      "args": ["tools/mcp_server.py"]
    }
  }
}
```

Available MCP tools:
- `get_vocabulary()`
- `validate_episode(episode_path)`
- `create_episode(episode_id, title, format_name, script_markdown, shots_json_content)`
- `voiceover(episode_path)`
- `build_scene(episode_path)`
- `contact_sheet(episode_path)`
- `render_pipeline(episode_path, final, only_stages, from_stage)`
- `thumbnail(episode_path)`
- `check_frame(episode_path, frame_number)`

---

## 💻 CLI Commands

You can run individual pipeline stages or the full tool suite directly from the command line:

```bash
# Query the engine vocabulary
python tools/roblox_tools.py vocab

# Validate an episode
python tools/roblox_tools.py validate episodes/wi_zlatan_bff

# Generate voiceover and word timings
python tools/roblox_tools.py voice episodes/wi_zlatan_bff

# Assemble Blender 3D scene
python tools/roblox_tools.py build episodes/wi_zlatan_bff

# Render QA contact sheet
python tools/roblox_tools.py sheet episodes/wi_zlatan_bff

# Render preview video (fast 540x960)
python tools/roblox_tools.py render episodes/wi_zlatan_bff

# Render final production video (1080x1920) + publish bundle
python tools/roblox_tools.py render episodes/wi_zlatan_bff --final
```

---

## 🧪 Automated Testing

Run the included automated test suite to verify tool functionality, OpenAPI schemas, bridge server endpoints, and Blender scene resolution:

```bash
python -m unittest tests/test_tools.py -v
```

---

## 📁 Repository Structure

```
├── .claude/                   # Claude agent skills
├── ai_studio/                 # Google AI Studio tool definitions & runners
│   ├── STUDIO_GUIDE.md        # Comprehensive Google AI Studio walkthrough
│   ├── gemini_director.py     # Automated Gemini agent with Function Calling
│   ├── openapi.json           # OpenAPI 3.0 specification for 1-click AI Studio import
│   ├── studio_bridge_server.py# Local web UI & REST API bridge for AI Studio
│   ├── system_prompt.txt      # System Instructions for Gemini
│   └── tools_schema.json      # Function Declaration JSON schemas
├── episodes/                  # Episode workspaces
│   ├── wi_zlatan_bff/         # Example episode: Zlatan & Theo
│   ├── test_engine/           # Test fixture episode
│   └── SHOTLIST_FORMAT.md     # Full shots.json specification guide
├── formats/                   # Format guides & styles (what_if, in_this_town)
├── pipeline/                  # Core Blender & Python engine scripts
│   ├── episode.py             # Blender 3D scene builder
│   ├── edit.py                # Blender VSE audio & caption editor
│   ├── render.py              # Blender render executor
│   ├── roblox_rig.py          # Character generator & facial atlas
│   ├── roblox_motions.py      # Poses & keyframed motion clips
│   ├── roblox_sets.py         # Sets, dressings & marks
│   ├── props.py               # 58 3D hand and world props
│   ├── validate.py            # Shot list validator
│   ├── vocab.py               # Vocabulary inspector
│   └── voiceover.py           # ElevenLabs / Edge TTS voice synthesizer
├── public/                    # 3D assets, fonts, audio, presets
│   ├── audio/                 # SFX and background music
│   └── roblox/                # Rig templates, sets, and props
├── publish/                   # Finished upload-ready shorts
├── tests/                     # Automated test suite
│   └── test_tools.py          # Unit & integration tests
├── tools/                     # Programmatic tool interfaces & servers
│   ├── roblox_tools.py        # Python API and CLI tool wrapper
│   └── mcp_server.py          # Model Context Protocol (FastMCP) server
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🎨 Creative Vocabulary

| Element | Available Options |
|---|---|
| **Cast Presets** | `Theo`, `Zlatan`, `King`, `Officer`, `Lily`, `Max`, `Mom`, `Dad`, `Noob`, `Cameraman` (plus customizable characters) |
| **Sets** | `bedroom`, `classroom`, `kitchen`, `street` (with dressings: `day`, `night`, `sunset`) |
| **Poses** | `stand`, `relaxed`, `point`, `arms_crossed`, `shocked`, `scared`, `sad`, `celebrate`, `sit`, `lie`, `hold`, etc. |
| **Faces** | `smile`, `grin`, `worried`, `shocked`, `laugh`, `sleep`, `angry`, `sad`, `smirk`, `cry`, `nervous` |
| **Actions** | `idle`, `talk`, `walk_to`, `run_to`, `jump`, `celebrate`, `fall_back`, `wave`, `dance`, `spin`, `float`, `poof` |
| **Props (58)** | `soccer_ball`, `trophy`, `poster`, `pizza`, `burger`, `phone`, `donut`, `gold_bar`, `sword`, `shield`, `cat`, etc. |
| **SFX** | `boing`, `bonk`, `boom`, `buzzer`, `cartoon_run`, `ding`, `glitch`, `poof`, `pop`, `record_scratch`, `whoosh` |
| **Music Moods** | `curious`, `quirky`, `tension` |

---

## 📄 License

MIT License. Free to use, adapt, and build viral 3D shorts.
