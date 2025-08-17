'''
Smart Terminal Agent: Natural Language -> Shell Command
Provides:
- parse_nl: map common NL intents to a safe, single shell command
- execute_command: run a command via ShellInterface
- execute_nl: parse then execute
Optional LLM fallback (disabled by default).
'''

from __future__ import annotations
import re
import shlex
from typing import Optional, Tuple

from src.shell import ShellInterface
from src.llm import llmInterface
from src.prompt import smart_terminal_prompt
from src.schema import SmartTerminalResponse


class SmartTerminalAgent:
    def __init__(
        self,
        use_llm: bool = False,
        model: str = "gpt-4.1-mini",
        api_key: Optional[str] | None = None,
        shell: Optional[ShellInterface] | None = None,
        timeout_seconds: Optional[int] = None,
        max_capture: Optional[int] = None,
    ) -> None:
        self.use_llm = use_llm
        self.model = model
        self.api_key = api_key
        self.llm: Optional[llmInterface] = None
        self.shell = shell or ShellInterface(timeout_seconds=timeout_seconds, max_capture=max_capture)

    def _ensure_llm(self) -> None:
        if self.llm is None:
            self.llm = llmInterface(api_key=self.api_key, model=self.model)

    # --------------- NL Parsing ---------------
    def parse_nl(self, text: str) -> str:
        """Translate a natural language request into a single safe shell command.
        Favors read-only and safe flags. Returns the original text if it already
        looks like a shell command or if no mapping is found.
        """
        t = (text or "").strip()
        lower = t.lower()

        # If it already looks like a command, pass through
        if lower.startswith((
            "ls", "pwd", "cd ", "cat ", "sed ", "grep ", "find ", "echo ",
            "mkdir ", "rmdir ", "rm ", "git ", "pip ", "python ", "pytest ",
            "./", "bash ", "sh ",
        )):
            return t

        def extract_after(phrase: str, default: str = "") -> str:
            idx = lower.find(phrase)
            if idx >= 0:
                return t[idx + len(phrase):].strip()
            return default

        # List files / directories
        if "list" in lower and ("file" in lower or "directory" in lower or "dir" in lower or "folders" in lower):
            path = "."
            m = re.search(r"in\s+(the\s+)?(?P<p>[\w\./\-*_]+)", lower)
            if m:
                path = m.group("p")
            if any(w in lower for w in ["all", "detailed", "details"]):
                return f"ls -la {shlex.quote(path)}"
            return f"ls -l {shlex.quote(path)}"

        if "show" in lower and ("files" in lower or "contents of directory" in lower):
            path = "."
            m = re.search(r"(in|of)\s+(the\s+)?(?P<p>[\w\./\-*_]+)", lower)
            if m:
                path = m.group("p")
            return f"ls -la {shlex.quote(path)}"

        # Current directory
        if "current directory" in lower or "where am i" in lower or "what directory" in lower or lower.strip() in ("pwd", "print working directory"):
            return "pwd"

        # Show/read file (cap first 200 lines for safety); preserve original case of filename
        for verb in ("show", "open", "view", "read", "print"):
            if lower.startswith(verb + " ") or f" {verb} " in lower:
                # Try patterns on original text to preserve case; ignore case for matching
                m = re.search(rf"{verb}\s+(the\s+)?file\s+(?P<f>.+)$", t, flags=re.IGNORECASE)
                if not m:
                    m = re.search(rf"{verb}\s+(?P<f>[\w\./\-]+)$", t, flags=re.IGNORECASE)
                if m:
                    f_raw = m.group("f").strip().strip('\"').strip("'")
                    return f"sed -n '1,200p' {shlex.quote(f_raw)}"

        # Search for a pattern in files
        if "search" in lower or "find in files" in lower or "look for" in lower:
            # Try to get a quoted pattern first
            pat: Optional[str] = None
            m = re.search(r"([\'\"])(?P<q>.+?)\1", t)
            if m:
                pat = m.group("q")
            else:
                m = re.search(r"(for|search)\s+(?P<pat>[\w\-\._]+)", lower)
                if m:
                    pat = m.group("pat")
            target = "."
            m2 = re.search(r"in\s+(?P<dir>[\w\./\-_]+)", lower)
            if m2:
                target = m2.group("dir")
            if not pat:
                pat = extract_after("search for", "").strip() or extract_after("look for", "").strip()
            if not pat:
                pat = lower
            return f"grep -R --line-number --color=never {shlex.quote(pat)} {shlex.quote(target)}"

        # Find a file by name
        if lower.startswith("find ") or ("find" in lower and "file" in lower):
            name: Optional[str] = None
            m = re.search(r"named\s+([\'\"])?(?P<n>.+?)\1($|\s)", lower)
            if m:
                name = m.group("n")
            if not name:
                m = re.search(r"find\s+(?P<n>[\w\.\-*_]+)", lower)
                if m:
                    name = m.group("n")
            if not name:
                after = extract_after("find", "")
                name = after.split()[0] if after else "*"
            return f"find . -name {shlex.quote(name)}"

        # Make directory
        if ("make" in lower or "create" in lower) and ("directory" in lower or "folder" in lower):
            m = re.search(r"(directory|folder)\s+(named\s+)?(?P<n>[\w\.\-_\/]+)", lower)
            if m:
                return f"mkdir -p {shlex.quote(m.group('n'))}"

        # Remove file/dir (use interactive/safe flags)
        if "remove" in lower or "delete" in lower or "rm " in lower:
            m = re.search(r"(file|folder|directory)\s+(?P<n>[\w\.\-_\/]+)", lower)
            if m:
                name = m.group("n")
                if "dir" in lower or "folder" in lower or "directory" in lower:
                    return f"rm -rI {shlex.quote(name)}"
                return f"rm -i {shlex.quote(name)}"

        # Show environment
        if "env" in lower and ("show" in lower or "print" in lower or "list" in lower):
            return "env | sort"

        # Disk usage / size
        if "disk" in lower or "space" in lower or "size of" in lower:
            m = re.search(r"size of\s+(?P<p>[\w\./\-_]+)", lower)
            path = m.group("p") if m else "."
            return f"du -sh {shlex.quote(path)}"

        # Git status
        if "git" in lower and "status" in lower:
            return "git status -sb"

        # Run tests
        if "run tests" in lower or "pytest" in lower:
            return "pytest -q"

        # Install dependencies
        if "install requirements" in lower or "install dependencies" in lower:
            return "pip install -r requirements.txt"

        # Fallback: optional LLM
        if self.use_llm:
            try:
                self._ensure_llm()
                # Provide the user input to the model; schema guides structured output
                input_text = str({"user_input": t, "instructions": smart_terminal_prompt.get("System", "")})
                res = self.llm.generate_response(input_text, text_format=SmartTerminalResponse)
                try:
                    if isinstance(res, SmartTerminalResponse):
                        return res.command
                    # If SDK returns a dict-like
                    return getattr(res, "command", None) or res.get("command", t)  # type: ignore
                except Exception:
                    return t
            except Exception:
                return t

        # As a last resort, return raw
        return t

    # --------------- Execution ---------------
    def execute_command(self, command: str) -> Tuple[str, str]:
        return self.shell.execute_command(command)

    def execute_nl(self, user_input: str) -> Tuple[str, Tuple[str, str]]:
        cmd = self.parse_nl(user_input)
        out = self.execute_command(cmd)
        return cmd, out