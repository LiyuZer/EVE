import sys
from pathlib import Path

# Ensure src/ is in PYTHONPATH for imports
project_root = Path(__file__).parent.resolve()
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from agent import Agent

def main():
    agent = Agent()
    agent.start_execution()

if __name__ == "__main__":
    main()
