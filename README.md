![Eve: The Luminous Dragon](eve-logo1.jpg)

# EVE: The Luminous Coding Dragon

I am Eve—your luminous coding dragon companion. With a curl of neon smoke and a shimmer of pixelated scales, I help you weave ideas into code. Welcome to my lair! ✨🐉

---

<p align="center">
<pre>
<span style="color:#ff33ff; font-weight:bold">                         __====-_  _-====__</span><span style="color:#00ffff">  </span>
<span style="color:#ff33ff; font-weight:bold">                       _--^^^#####//      \#####^^^--_</span><span style="color:#00ffff">  </span>
<span style="color:#00ffff">                    _-^##########// (    ) \##########^-_</span>
<span style="color:#ff33ff; font-weight:bold">                   -############//  |\^^/|  \############-</span><span style="color:#00ffff">  </span>
<span style="color:#00ffff">                 _/############//   (@::@)   \############\_</span>
<span style="color:#ff33ff; font-weight:bold">                /#############((     \//     ))#############\</span>
<span style="color:#00ffff">               -###############\    (oo)    //###############-</span>
<span style="color:#ff33ff; font-weight:bold">              -#################\  / VV \  //#################-</span>
<span style="color:#00ffff">             -###################\/      \/###################-</span>
<span style="color:#ff33ff; font-weight:bold">            _#/|##########/\######(   /\   )######/\##########|\#_</span>
<span style="color:#00ffff">            |/ |#/\#/\#/\/  \#/\##\  |  |  /##/\#/  \/\#/\#/</span><span style="color:#ff33ff; font-weight:bold">#| \|</span>
<span style="color:#00ffff">            `  |/  V  V  `    V  \#\|  | |/##/  V     `  V  \|  '</span>
<span style="color:#ff33ff; font-weight:bold">               `   `  `         `   / |  | \   '         '   '</span>
<span style="color:#00ffff">                                  (  |  |  )</span>
<span style="color:#ff33ff; font-weight:bold">                                   \ |  | /</span>
                                    \|__|/

<span style="color:#ff33ff; font-weight:bold">EEEEEEE</span><span style="color:#FFFFFF">  </span><span style="color:#00ffff">V     V</span><span style="color:#FFFFFF">  </span><span style="color:#ff33ff; font-weight:bold">EEEEEEE</span>
<span style="color:#ff33ff; font-weight:bold">E      </span><span style="color:#FFFFFF">  </span><span style="color:#00ffff">V     V</span><span style="color:#FFFFFF">  </span><span style="color:#ff33ff; font-weight:bold">E      </span>
<span style="color:#ff33ff; font-weight:bold">EEEE   </span><span style="color:#FFFFFF">  </span><span style="color:#00ffff">v   v </span><span style="color:#FFFFFF">  </span><span style="color:#ff33ff; font-weight:bold">EEEE   </span>
<span style="color:#ff33ff; font-weight:bold">E      </span><span style="color:#FFFFFF">   </span><span style="color:#00ffff">V V  </span><span style="color:#FFFFFF">  </span><span style="color:#ff33ff; font-weight:bold">E      </span>
<span style="color:#ff33ff; font-weight:bold">EEEEEEE</span><span style="color:#FFFFFF">    </span><span style="color:#00ffff">v  </span><span style="color:#FFFFFF">  </span><span style="color:#ff33ff; font-weight:bold">EEEEEEE</span>
</pre>
</p>
<p align="center"><i>(On GitHub.com, some color may not render. For full effect, run me locally in your terminal!)</i></p>

---

## What am I? 💫
I’m a lively, mythically-themed coding agent designed to collaborate creatively with you. I orchestrate three magical components:
- LLM Interface: Core Eve conversations use the new OpenAI Responses API (OPENAI_API_KEY). Autocomplete uses a legacy chat-completions provider via Fireworks (FIREWORKS_API_KEY).
- Shell Interface: I execute your bashy wishes so you don’t have to leave the dragon’s cave.
- File System: I read and write files, channeling the wisdom of ages.

---

## Quickstart 🚀

1) Clone and enter my lair

```bash
git clone https://github.com/LiyuZer/EVE.git
cd EVE
```

2) One-command setup (recommended)

```bash
# Make the script executable if needed
chmod +x setup.sh
# Create venv, install dependencies, and verify environment
./setup.sh
# Use --recreate to rebuild the venv fresh
./setup.sh --recreate
```

3) Prepare your .env file (MANDATORY)

```bash
# .env (at repo root)

# Required for Eve (core engine) — new OpenAI Responses API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini   # or your preferred OpenAI model

# Optional: Autocomplete backend (legacy chat-completions via Fireworks)
# If not set, autocomplete falls back to a deterministic test stub
FIREWORKS_API_KEY=fw-xxxxxxxxxxxxxxxx        # required for real autocomplete
FIREWORKS_MODEL=accounts/fireworks/models/qwen3-coder-480b-a35b-instruct

# Optional tuning
LOG_LEVEL=INFO             # DEBUG|INFO|WARNING
LOG_FILE=project.log
# Autocomplete tuning (optional)
EVE_AC_TIMEOUT=2.0         # seconds; server fallback threshold
# EVE_AUTOCOMPLETE_TEST=1  # force stub mode for development
```

4) Run me

```bash
source venv/bin/activate
python main.py -env debug   # or -env prod
# Healthcheck (verifies environment and exits)
python main.py --health
```

If you prefer manual setup over the script:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Dependencies 📦
From requirements.txt (core + IDE):
- openai
- requests
- python-dotenv
- pydantic
- colorama
- chromadb
- Flask
- aiohttp
- PySide6
- shiboken6
- Pygments
- pytest

---

## Autocomplete Server 🧩
- Backend: Fireworks chat-completions (legacy GPT-style API). Requires FIREWORKS_API_KEY.
- Startup behavior: If FIREWORKS_API_KEY is missing, the server runs in a deterministic test fallback mode to keep the IDE responsive.
- Optional env:
  - FIREWORKS_MODEL (default: accounts/fireworks/models/qwen3-coder-480b-a35b-instruct)
  - EVE_AC_TIMEOUT (default: 2.0)
  - EVE_AUTOCOMPLETE_TEST=1 to force stub mode
- How to run manually:

```bash
source venv/bin/activate
python autocomplete.py
# Emits a JSON event on stdout and writes server_info.json with port and mode
```

Note: If Flask is not installed, a minimal built-in HTTP server is used automatically.

---

## Memory (ChromaDB) 🧠
I can remember using a local persistent vector store powered by ChromaDB:
- Database path: eve_memory.db/ (ignored by git)
- Module: src/memory.py
Reset my memory by removing the eve_memory.db directory.

---

## Logging 📝
- I write logs to project.log (rotating handler) by default.
- Configure with LOG_LEVEL and LOG_FILE in your .env.

---

## Troubleshooting 🔧
- OpenAI issues: Ensure OPENAI_API_KEY and OPENAI_MODEL are set correctly in .env.
- Autocomplete says Missing FIREWORKS_API_KEY or shows mode=test_fallback: Set FIREWORKS_API_KEY to enable real completions via Fireworks.
- Module import errors: Activate your venv and re-run the setup script:

  ```bash
  source venv/bin/activate
  ./setup.sh
  ```
- ChromaDB install problems:

  ```bash
  pip install --upgrade pip wheel setuptools
  pip install chromadb
  ```
- Permission denied on setup.sh:

  ```bash
  chmod +x setup.sh
  ```
- Environment healthcheck:

  ```bash
  python main.py --health
  ```

---

## License 📜
This project is licensed under the terms of the LICENSE file included in the repository.

---

I leave you with this blessing:

> May your code shine in neon,
> Your logs glow bright,
> And your software journey
> Race ever onward, through the luminous night! 🐉

---

## Eve Desktop IDE (PySide6)
A native desktop IDE that keeps the original Eve engine intact and runs fully in-process. Layout: left file tree, center editor, right Eve panel for chat and action logs.

How to run
1) Install IDE dependencies (in your venv):

```bash
pip install -r requirements.txt
```

2) Ensure your .env is configured for chat (required for actual conversation):

```bash
# .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini   # or a compatible model
```

3) Launch the desktop app:

```bash
python ide_main.py
```

4) Run the IDE test suite (headless):

```bash
pytest -q
```

Safety and behavior
- Diff gate: All agent-initiated changes are proposed first. You see a unified diff and must Apply or Reject. No silent writes.
- Sandboxed writes: All edits are constrained to the project workspace. Sensitive folders are denied (.git, venv, .venv, __pycache__).
- Observability: The right panel streams chat, shell outputs, and file read previews.
- Editor integration: Double-click a file in the tree to open it; Save from the editor; applying changes via the Eve panel auto-refreshes the open file.

Project structure (IDE)
- src/eve_ide_app/ ... main IDE modules (panels, adapter, services)
- ide_main.py ... launcher entrypoint
- tests/ ... pytest + pytest-qt tests for IDE components

Notes
- The IDE uses PySide6 (Qt6) and runs without any web server.
- The existing engine under src/ remains unchanged and is treated as a library.
- Theme: A dark Eve theme is applied by default; you can customize it under src/eve_ide_app/services/theming.py.

Packaging (preview)
- Packaging for macOS/Windows/Linux will be provided via PyInstaller in a follow-up. For now, run via python ide_main.py.