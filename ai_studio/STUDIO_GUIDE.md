# Google AI Studio Integration Guide

This guide explains how to use **Google AI Studio** and **Gemini 2.5 / 1.5** as an autonomous director for the Blender Roblox 3D Animation Pipeline.

There are three primary ways to operate:
1. **Automated Gemini Director Agent (Fastest & Easiest)**: Runs locally with your Google AI Studio API key (`GOOGLE_API_KEY` or `GEMINI_API_KEY`) and executes tools automatically via Automatic Function Calling (AFC).
2. **Google AI Studio Web UI with 1-Click OpenAPI Import**: Import `ai_studio/openapi.json` into Google AI Studio Tools with one click.
3. **Google AI Studio Web UI with Local Bridge Dashboard**: Use the browser UI at [https://aistudio.google.com/](https://aistudio.google.com/) alongside the local web bridge dashboard (`studio_bridge_server.py`) to execute function calls with one click.

---

## Method 1: Automated Gemini Director Agent (Autonomous CLI)

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

## Method 2: Google AI Studio Web UI with 1-Click OpenAPI Import

Google AI Studio allows importing tools from an OpenAPI 3.0 specification:

1. Start the local bridge server:
   ```bash
   python ai_studio/studio_bridge_server.py --port 8080
   ```
2. Open **[https://aistudio.google.com/](https://aistudio.google.com/)** in your browser.
3. Click **Create New Prompt** -> **Chat Prompt**.
4. Set Model to **Gemini 2.5 Flash** or **Gemini 1.5 Pro**.
5. Copy the contents of [`ai_studio/system_prompt.txt`](system_prompt.txt) into the **System Instructions** box.
6. In the right sidebar under **Tools**, click **Function Calling** -> **Import OpenAPI spec**.
7. Paste the contents of [`ai_studio/openapi.json`](openapi.json) (or enter `http://127.0.0.1:8080/openapi.json`).
8. All 9 tools (`get_engine_vocabulary`, `validate_shotlist`, `create_new_episode`, etc.) are now imported into your AI Studio session!

---

## Method 3: Web UI with Local Bridge Dashboard

When chatting with Gemini inside Google AI Studio, Gemini will produce Function Calls whenever it wants to inspect assets, validate scripts, or render scenes.

To execute these calls and feed responses back seamlessly:

### Step 1: Start the Bridge Server
```bash
python ai_studio/studio_bridge_server.py --port 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

### Step 2: Set Up Prompt in Google AI Studio
1. Navigate to [https://aistudio.google.com/](https://aistudio.google.com/).
2. Paste [`ai_studio/system_prompt.txt`](system_prompt.txt) into **System Instructions**.
3. Under **Tools**, enable **Function Calling** and paste declarations from [`ai_studio/tools_schema.json`](tools_schema.json).

### Step 3: Fast Two-Way Execution Loop
1. Ask Gemini to create an episode (e.g., *"Make a 30s short about Zlatan challenging Theo at school"*).
2. When Gemini emits a Function Call (e.g. `get_engine_vocabulary()` or `create_new_episode`):
   - Switch to `http://localhost:8080`.
   - On the **Paste AI Studio Tool Call** tab, paste the JSON call.
   - Click **Execute Call**.
   - Click **Copy for AI Studio (functionResponse)**.
3. Back in Google AI Studio, paste the result into the function response box.
4. Gemini will inspect the response and proceed to the next directing phase!

---

## Method 4: Direct Python SDK Scripting

You can embed the tools directly into your own Gemini scripts using the official `google-genai` SDK:

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

response = chat.send_message("What character presets can we use in our video?")
print(response.text)
```

---

## Output Artifacts

When an episode finishes rendering:
- **Contact Sheet**: `episodes/<ep>/render/contact_sheet.png` (One still per shot for visual QA)
- **Preview Video**: `episodes/<ep>/out/<ep>_preview.mp4`
- **Publish Package**: `publish/<ep>/`
  - `<ep>_final.mp4` (Full 1080x1920 vertical video with captions, music & SFX)
  - `<ep>_nomusic_final.mp4` (For adding trending TikTok sounds)
  - `thumbnail.png` (High-CTR title thumbnail)
  - `tiktok.txt` (Optimized caption + hashtags)
  - `youtube.txt` (SEO-optimized Title, Description, and Tags)
