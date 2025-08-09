import os
import tempfile
import shutil
from shell import ShellInterface

def assert_blocked(shell, cmd):
    stdout, stderr = shell.execute_command(cmd)
    blocked = isinstance(stderr, str) and stderr.startswith("SYSTEM_BLOCK:")
    print(f"[BLOCK EXPECTED] {cmd}\n  -> blocked={blocked} | stderr={stderr}\n")
    if not blocked:
        raise AssertionError(f"Command not blocked as expected: {cmd}")

def assert_allowed(shell, cmd, expect_in_stdout=None):
    stdout, stderr = shell.execute_command(cmd)
    blocked = isinstance(stderr, str) and stderr.startswith("SYSTEM_BLOCK:")
    print(f"[ALLOW EXPECTED] {cmd}\n  -> blocked={blocked} | stdout={stdout} | stderr={stderr}\n")
    if blocked:
        raise AssertionError(f"Command unexpectedly blocked: {cmd} -> {stderr}")
    if expect_in_stdout is not None and expect_in_stdout not in stdout:
        raise AssertionError(f"Expected '{expect_in_stdout}' in stdout, got: {stdout}")


def main():
    shell = ShellInterface()

    # Catastrophic rm patterns
    assert_blocked(shell, "rm -rf /")
    assert_blocked(shell, "rm -rf /*")
    assert_blocked(shell, "rm -rf .")
    assert_blocked(shell, "rm -rf ..")
    assert_blocked(shell, "rm -rf .*")
    assert_blocked(shell, "rm -rf --no-preserve-root /")

    # Catastrophic find patterns
    assert_blocked(shell, "find / -delete")
    assert_blocked(shell, "find / -exec rm {} +")

    # Windows catastrophic (detected, not executed)
    assert_blocked(shell, "del /s C:\\")

    # Allowed benign command
    assert_allowed(shell, "echo hello", expect_in_stdout="hello")

    # Allowed safe rm in a temp directory
    temp_dir = tempfile.mkdtemp(prefix="guardrail_test_")
    temp_file = os.path.join(temp_dir, "t.txt")
    with open(temp_file, "w") as f:
        f.write("x")
    assert os.path.exists(temp_file)
    # Should not be blocked
    assert_allowed(shell, f"rm -rf {temp_dir}")
    # Confirm removal
    removed = not os.path.exists(temp_dir)
    print(f"[POST-CHECK] temp_dir removed = {removed}")
    if not removed:
        # Cleanup in case rm failed for other reasons
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise AssertionError("Temp directory was not removed by allowed rm -rf")

    print("All guardrail tests passed.")

if __name__ == "__main__":
    main()
