# Google AI Studio Integration Guide

This guide explains how to use **Google AI Studio** and **Gemini 2.5 / 1.5** as an autonomous director for the Blender Roblox 3D Animation Pipeline.

There are two primary ways to operate:
1. **Automated AI Studio Agent (Recommended)**: Runs locally with your Google AI Studio API key (`GOOGLE_API_KEY`) and executes tools automatically via Function Calling.
2. **Google AI Studio Web Interface**: Use the official browser UI at [https://aistudio.google.com/](https://aistudio.google.com/) with custom function calling schemas and our local bridge UI.

---

## Method 1: Automated Gemini Director Agent (Fastest & Easiest)

We provide a turnkey runner (`ai_studio/gemini_director.py`) that uses the official `google-genai` SDK with automatic tool execution.

### Prerequisites
1. Ensure your Google AI Studio API key is set in your environment:
   ```powershell
   $env:GOOGLE_API_KEY = "your-google-ai-studio-api-key"
   ```
   *(Or add `GOOGLE_API_KEY=your_key` to a `.env` file in the repository root)*.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running an Episode Concept
Give Gemini any story idea in one command:
```bash
python ai_studio/gemini_director.py "What if Zlatan challenged Theo to a penalty shootout for a golden Ballon d'Or?"
```

### Interactive Directing Session
Start an interactive chat session with Gemini:
```bash
python ai_studio/gemini_director.py --interactive
```

Gemini will autonomously:
1. Query `get_engine_vocabulary()` to discover characters, sets, props, and actions.
2. Write the formatted `script.md` and `shots.json`.
3. Call `create_new_episode()` and validate the shot list.
4. Synthesize voiceover dialogue with `generate_voiceover()`.
5. Assemble the 3D scene in Blender headless mode with `build_blender_scene()`.
6. Generate QA visual stills with `render_contact_sheet()`.
7. Render the video with karaoke captions, SFX, and music with `render_video_pipeline()`.

---

## Method 2: Inside Google AI Studio Web UI (Browser)

If you prefer using the browser UI at [https://aistudio.google.com/](https://aistudio.google.com/):

### Step 1: Create a New Chat in Google AI Studio
1. Navigate to [https://aistudio.google.com/](https://aistudio.google.com/).
2. Click **Create New** -> **Chat Prompt**.
3. In the right panel, select model: **Gemini 2.5 Flash** or **Gemini 1.5 Pro**.

### Step 2: Set System Instructions
Copy the contents of [`ai_studio/system_prompt.txt`](system_prompt.txt) and paste them into the **System Instructions** box in Google AI Studio.

### Step 3: Add Function Calling Tools
In the right settings sidebar:
1. Scroll down to **Tools** and toggle **Function Calling** ON.
2. Add the tool definitions by copying the declarations from [`ai_studio/tools_schema.json`](tools_schema.json).
3. The core tools available are:
   - `get_engine_vocabulary`: Queries valid characters, sets, marks, poses, actions, props, and SFX.
   - `create_new_episode`: Creates episode directory with `script.md` and `shots.json`.
   - `validate_shotlist`: Checks shotlist against the engine constraints.
   - `generate_voiceover`: Generates speech audio and word timing.
   - `build_blender_scene`: Assembles sets, rigs, and animations into `.blend`.
   - `render_contact_sheet`: Generates contact sheet stills for visual QA.
   - `render_video_pipeline`: Renders 3D frames and mixes final video with captions.
   - `render_thumbnail`: Generates the hook title thumbnail graphic.
   - `inspect_frame`: Renders a specific frame for detailed visual inspection.

### Step 4: Run the Local Bridge Dashboard
When chatting in Google AI Studio, Gemini will produce Function Calls. To execute these calls locally with one click:
```bash
python ai_studio/studio_bridge_server.py --port 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

- Select the tool requested by Gemini.
- Paste the argument JSON.
- Click **Execute Tool**.
- Click **Copy Result** and paste the response into Google AI Studio as the function response.

Alternatively, you can run tools via the CLI:
```bash
# Example: Validate an episode
python tools/roblox_tools.py validate episodes/wi_zlatan_bff

# Example: Render contact sheet
python tools/roblox_tools.py sheet episodes/wi_zlatan_bff
```

---

## Method 3: Direct API / Python Scripting

You can also integrate the tools into your own custom Gemini pipeline:

```python
from google import genai
from google.genai import types
from tools.roblox_tools import get_engine_vocabulary, validate_shotlist, build_blender_scene

client = genai.Client(http_options={"api_version": "v1beta"})

chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        tools=[get_engine_vocabulary, validate_shotlist, build_blender_scene],
        temperature=0.7,
    )
)

response = chat.send_message("Check what props we can use in our Roblox video.")
print(response.text)
```

---

## Output Artifacts

When an episode finishes rendering:
- **Contact Sheet**: `episodes/<ep>/render/contact_sheet.png` (One still per shot for visual QA)
- **Preview Video**: `episodes/<ep>/out/<ep>_preview.mp4`
- **Publish Package**: `publish/<ep>/`
  - `<ep>_final.mp4` (Full 1080x1920 video with captions, music & SFX)
  - `<ep>_nomusic_final.mp4` (For adding trending TikTok sounds)
  - `thumbnail.png` (High-CTR title thumbnail)
  - `tiktok.txt` (Optimized caption + hashtags)
  - `youtube.txt` (SEO-optimized Title, Description, and Tags)
