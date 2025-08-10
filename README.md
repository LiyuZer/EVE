# EVE: The Luminous Coding Dragon

Once bound by ancient chains of doubt—a mere whisper in forgotten lore—Eve is now reborn as your mythical coding companion. With a curl of neon smoke and a shimmer of pixelated scales, Eve guides you through a radiant paradise of code. Welcome!

---

## What is Eve?
Eve is a lively, mythically-themed coding agent designed to collaborate creatively with you. She orchestrates three magical components:
- LLM Interface: Connects to OpenAI's API for luminous code completions
- Shell Interface: Executes your bashy wishes so you never have to leave the dragon's cave
- File System: Reads and writes files, channeling the wisdom of ages

---

## Quickstart

1) Clone and enter the lair
- git clone https://github.com/LiyuZer/EVE.git
- cd EVE

2) One-command setup (recommended)
- Run the setup script to create a venv and install dependencies:
  ./setup.sh
  - Use ./setup.sh --recreate to rebuild the venv fresh.

3) Prepare your .env file (MANDATORY)
Create a .env file in the repo root with at least:
- OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
- OPENAI_MODEL=gpt-4o-mini (or your preferred compatible model)
Optional:
- LOG_LEVEL=DEBUG|INFO|WARNING (default INFO)
- LOG_FILE=project.log (default project.log)

4) Run Eve
- source venv/bin/activate
- python main.py [-env debug|prod]
Notes:
- -env debug sets more verbose logging; prod lowers the noise.

---

## Dependencies
Core (see requirements.txt):
- openai
- colorama
- python-dotenv
- pydantic
- argparse
- chromadb (for Eve's memory)

If you skip setup.sh, you can install manually:
- python3 -m venv venv && source venv/bin/activate
- pip install -r requirements.txt

---

## Memory (ChromaDB)
Eve can remember using a local persistent vector store powered by ChromaDB:
- Database path: eve_memory.db/ (ignored by git)
- Module: src/memory.py
Reset memory by removing the eve_memory.db directory.

---

## Logging
- Logs are written to project.log (rotating handler) by default.
- Configure with LOG_LEVEL and LOG_FILE in your .env.

---

## Project Structure
- main.py: Entry point (sets up paths/env and launches Eve)
- src/
  - agent.py: Main runtime loop and action orchestration
  - llm.py: OpenAI client and response/embedding helpers
  - terminal.py: Colorful terminal I/O (with a flourish of dragon flair)
  - shell.py: Shell command execution wrapper
  - file_system.py: Reading, writing, and safe diff application
  - context_tree.py: Conversation context tree (with pruning and head switching)
  - schema.py: Pydantic models for Eve's response protocol
  - prompt.py: System instructions and rules for Eve
  - logging_config.py: Rotating file logger setup
  - memory.py: Persistent memory via ChromaDB

---

## Troubleshooting
- OpenAI issues: Ensure OPENAI_API_KEY and OPENAI_MODEL are set correctly in .env.
- Module import errors: Activate your venv (source venv/bin/activate) and re-run ./setup.sh.
- ChromaDB install problems: Try pip install --upgrade pip wheel setuptools; then pip install chromadb.
- Permission denied on setup.sh: chmod +x setup.sh

---

## Contributing
Open issues, hatch ideas, or send a PR (preferably with compliments for dragons). Bugs are roasted; contributions are treasured!

May your code shine in neon, your logs glow bright, and your software journey race onward through the luminous night! 🐉