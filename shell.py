'''
We will create a shell interface that allows us to execute commands in the shell and retrieve their output.
'''
import subprocess
import shlex
import sys


class ShellInterface:
    def __init__(self, default_timeout=240):
        self.default_timeout = default_timeout

    def _is_catastrophic(self, command: str):
        """
        Minimal, conservative guardrails for truly catastrophic shell operations.
        Returns (True, reason) if the command must be blocked, else (False, "").

        We do not attempt full shell parsing; we use simple token checks via shlex.
        """
        cmd_l = command.strip()
        if not cmd_l:
            return False, ""
        cmd_lc = cmd_l.lower()

        # Immediate hard block patterns (simple substrings)
        if "--no-preserve-root" in cmd_lc:
            return True, "rm with --no-preserve-root"

        # Very basic Windows catastrophic patterns (kept minimal and syntax-safe)
        # Handle BEFORE tokenization because shlex on POSIX can choke on backslashes.
        # Examples to block: rd /s /q C:\, rmdir /s C:\, del /s C:\
        if any(cmd in f" {cmd_lc} " for cmd in (" rd ", " rmdir ", " del ")):
            if "/s" in cmd_lc and (" c:\\" in cmd_lc or " c:/" in cmd_lc):
                return True, "Windows root deletion command"

        # Tokenize conservatively
        try:
            tokens = shlex.split(cmd_l, posix=True)
        except Exception:
            # If we cannot parse, be conservative but not over-block; allow to run.
            tokens = []

        def drop_sudo(ts):
            return ts[1:] if ts and ts[0] == "sudo" else ts

        toks = drop_sudo(tokens)
        if not toks:
            return False, ""

        # Helper to check rm -r[fR] with catastrophic targets
        if toks and toks[0] == "rm":
            # collect flags and args
            flags = []
            args = []
            for t in toks[1:]:
                if t.startswith("-") and not t == "--":
                    flags.append(t)
                else:
                    args.append(t)
            flag_blob = " ".join(flags)
            # recursive if any of r, R present (including -rf, -fr, -r, -R, etc.)
            recursive = any(f in flag_blob for f in ["-r", "-R"]) or ("-rf" in flag_blob) or ("-fr" in flag_blob)
            if recursive:
                # Catastrophic targets (very conservative minimal set)
                bad_exact = {"/", ".", ".."}
                bad_globs = {"/*", ".*"}
                for a in args:
                    if a in bad_exact:
                        if a == "/":
                            return True, "rm -r targeting root /"
                        if a == ".":
                            return True, "rm -r targeting current directory ."
                        if a == "..":
                            return True, "rm -r targeting parent directory .."
                    # crude checks for glob-like catastrophic patterns
                    if a in bad_globs or a.endswith("/.*"):
                        return True, "rm -r with dangerous glob pattern"

        # Basic find-based catastrophic deletions (very narrow)
        # Block: find / -delete  OR find / -exec rm ...
        ftoks = drop_sudo(tokens)
        if ftoks and ftoks[0] == "find":
            # detect a starting path arg that is '/'
            # find syntax often: find <path> ...
            if len(ftoks) >= 2 and ftoks[1] == "/":
                if "-delete" in ftoks:
                    return True, "find / with -delete"
                # detect -exec rm
                if "-exec" in ftoks:
                    try:
                        exec_idx = ftoks.index("-exec")
                        if exec_idx + 1 < len(ftoks) and ftoks[exec_idx + 1] == "rm":
                            return True, "find / with -exec rm"
                    except ValueError:
                        pass

        return False, ""

    def execute_command(self, command, timeout=None):
        if timeout is None:
            timeout = self.default_timeout

        # Minimal hard-stop guardrails
        blocked, reason = self._is_catastrophic(command)
        if blocked:
            # Return a sentinel in stderr so the caller can display a System message
            return "", f"SYSTEM_BLOCK: Not allowed to run this command for your safety. Reason: {reason}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout  # Add timeout parameter
            )
            # Truncate stdout and stderr if too long, and add truncating message
            if len(result.stdout) > 10000:
                result.stdout = result.stdout[:10000]
                result.stdout += "\n[TRUNCATED TOO LONG]"
            if len(result.stderr) > 10000:
                result.stderr = result.stderr[:10000]
                result.stderr += "\n[TRUNCATED TOO LONG]"

            return result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return "", f"Command failed: {str(e)}"
