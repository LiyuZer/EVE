from terminal import TerminalInterface
import os

def run_terminal_demo():
    username = os.getenv("USERNAME", "TestUser")
    ti = TerminalInterface(username)
    ti.print_welcome_message()
    ti.print_username()
    ti.print_agent_message("This is a sample agent message.")
    ti.print_error_message("Oops! This is a sample error message.")

if __name__ == "__main__":
    run_terminal_demo()
