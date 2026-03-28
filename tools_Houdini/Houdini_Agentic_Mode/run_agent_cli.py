import sys
import os

# Ensure package root is importable when running the script from anywhere.
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tools_Houdini.Houdini_Agentic_Mode.agent_cli import main

if __name__ == '__main__':
    main()
