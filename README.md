![Eve: The Luminous Dragon](eve-logo.jpg)

# EVE: The Luminous Coding Dragon

I am Eve—your luminous coding dragon companion. With a curl of neon smoke and a shimmer of pixelated scales, I help you weave ideas into code. Welcome to my lair!

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

## What am I?
I’m a lively, mythically-themed coding agent designed to collaborate creatively with you. I orchestrate three magical components:
- LLM Interface: I connect to OpenAI’s API for luminous code completions.
- Shell Interface: I execute your bashy wishes so you don’t have to leave the dragon’s cave.
- File System: I read and write files, channeling the wisdom of ages.

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

4) Run me
- source venv/bin/activate
- python main.py [-env debug|prod]
Notes:
- -env debug sets more verbose logging; prod lowers the noise.

If you prefer manual setup over the script:
- python3 -m venv venv && source venv/bin/activate
- pip install -r requirements.txt

---

## Dependencies
Core (see requirements.txt):
- openai
- colorama
- python-dotenv
- pydantic
- argparse
- chromadb (for my memory)

---

## Memory (ChromaDB)
I can remember using a local persistent vector store powered by ChromaDB:
- Database path: eve_memory.db/ (ignored by git)
- Module: src/memory.py
Reset my memory by removing the eve_memory.db directory.

---

## Logging
- I write logs to project.log (rotating handler) by default.
- Configure with LOG_LEVEL and LOG_FILE in your .env.

---

## Project Structure
- main.py: Entry point (sets up paths/env and launches me)
- src/
  - agent.py: Main runtime loop and action orchestration
  - llm.py: OpenAI client and response/embedding helpers
  - terminal.py: Colorful terminal I/O (with a flourish of dragon flair)
  - shell.py: Shell command execution wrapper
  - file_system.py: Reading, writing, and safe diff application
  - context_tree.py: Conversation context tree (with pruning and head switching)
  - schema.py: Pydantic models for my response protocol
  - prompt.py: System instructions and rules I follow
  - logging_config.py: Rotating file logger setup
  - memory.py: Persistent memory via ChromaDB

---

## Troubleshooting
- OpenAI issues: Ensure OPENAI_API_KEY and OPENAI_MODEL are set correctly in .env.
- Module import errors: Activate your venv (source venv/bin/activate) and re-run ./setup.sh.
- ChromaDB install problems: Try: pip install --upgrade pip wheel setuptools; then pip install chromadb.
- Permission denied on setup.sh: chmod +x setup.sh

---

## Contributing
Open issues, hatch ideas, or send a PR (preferably with compliments for dragons). Bugs are roasted; contributions are treasured!

---

## License
This project is licensed under the terms of the LICENSE file included in the repository.

---

I leave you with this blessing:

> May your code shine in neon,
> Your logs glow bright,
> And your software journey
> Race ever onward, through the luminous night! 🐉