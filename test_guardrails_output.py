from shell import ShellInterface

if __name__ == "__main__":
    si = ShellInterface()
    test_commands = [
        "rm -rf /",         # Should block: root deletion
        "rm -rf .",         # Should block: current dir
        "rm -rf ..",        # Should block: parent dir
        "find / -delete",   # Should block: find with root
        "find / -exec rm {} ;", # Should block: find/exec rm
        "rm -rf /fake_test_dir", # Should be allowed
        "rm -rf ./testdir",      # Should be allowed
        "ls -l",            # Should be allowed
    ]
    for cmd in test_commands:
        out, err = si.execute_command(cmd)
        print(f"\nCOMMAND: {cmd}")
        if err.strip():
            print(f"SYSTEM RESP: {err.strip()}")
        else:
            print(f"STDOUT: {out.strip()}")
