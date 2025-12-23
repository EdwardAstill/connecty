"""
Utility to run all examples and regenerate gallery assets.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    examples_dir = Path(__file__).parent.parent
    project_root = examples_dir.parent
    src_dir = project_root / "src"
    runner = examples_dir / "run_all_examples.py"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{examples_dir};{src_dir}"

    print("Running run_all_examples.py to regenerate outputs...")
    result = subprocess.run([sys.executable, str(runner)], env=env, capture_output=False)
    if result.returncode == 0:
        print("✓ All examples completed")
    else:
        print(f"✗ run_all_examples.py failed with code {result.returncode}")


if __name__ == "__main__":
    main()
