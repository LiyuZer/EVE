import sys
import argparse
import os
from pathlib import Path


def get_log_level_from_env(env_str: str):
    if env_str is None:
        return os.getenv("LOG_LEVEL", "INFO")
    env_str = env_str.strip().lower()
    if env_str in ["prod", "production", "personal"]:
        return "WARNING"
    if env_str in ["debug", "dev", "development"]:
        return "DEBUG"
    return "INFO"


def main():
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / 'src'

    # Temporary compatibility: ensure legacy intra-src imports still work
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    parser = argparse.ArgumentParser(description="Run the agent with specified environment mode.")
    parser.add_argument("-env", type=str, default=None, help="Set environment mode: prod or debug (sets logger level)")
    args, _ = parser.parse_known_args()

    log_level = get_log_level_from_env(args.env)
    os.environ["LOG_LEVEL"] = log_level

    # Import after setting LOG_LEVEL so loggers pick up the configured level
    from src.agent import Agent

    agent = Agent(src_path)
    agent.start_execution()


if __name__ == "__main__":
    main()