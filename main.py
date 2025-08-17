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
    parser.add_argument("--log", action="store_true", help="Print context tree structure during execution")
    parser.add_argument("--health", action="store_true", help="Run environment health checks and exit")
    parser.add_argument("--mode", type=str, default="console", choices=["console", "ide"],)
    args, _ = parser.parse_known_args()

    log_level = get_log_level_from_env(args.env)
    os.environ["LOG_LEVEL"] = log_level

    if args.log:
        os.environ["EVE_LOG_CONTEXT_TREE"] = "1"

    if args.health:
        # Delay import until explicitly requested to avoid side effects
        from src.utils.health import healthcheck_env
        ok, messages = healthcheck_env()
        print("HEALTHCHECK")
        for m in messages:
            print(f"- {m}")
        print("RESULT:", "OK" if ok else "FAIL")
        raise SystemExit(0 if ok else 1)

    # Import after setting LOG_LEVEL so loggers pick up the configured level
    from src.agent import Agent

    # Prefer IDE-selected workspace root from environment if provided
    workspace_root_env = os.getenv("EVE_WORKSPACE_ROOT")
    try:
        root_for_agent = Path(workspace_root_env).resolve() if workspace_root_env else src_path
    except Exception:
        root_for_agent = src_path

    agent = Agent(root_for_agent, args.mode)
    agent.start_execution()


if __name__ == "__main__":
    main()