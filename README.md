![Eve: The Luminous Dragon](eve-logo.jpg)

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
- LLM Interface: I connect to OpenAI’s API for luminous code completions.
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
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini   # or your preferred compatible model
# Optional tuning
LOG_LEVEL=INFO             # DEBUG|INFO|WARNING
LOG_FILE=project.log
```

4) Run me

```bash
source venv/bin/activate
python main.py -env debug   # or -env prod
```

If you prefer manual setup over the script:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Dependencies 📦
Core (see requirements.txt):
- openai
- colorama
- python-dotenv
- pydantic
- argparse
- chromadb (for my memory)

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

---

## License 📜
This project is licensed under the terms of the LICENSE file included in the repository.

---

I leave you with this blessing:

> May your code shine in neon,
> Your logs glow bright,
> And your software journey
> Race ever onward, through the luminous night! 🐉