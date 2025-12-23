"""
Run all bolt-focused connecty examples.
"""
import os
import subprocess
import sys
from pathlib import Path

examples_dir = Path(__file__).parent
src_dir = examples_dir.parent / "src"

bolt_examples = [
    "bolt analysis/bolt_group_analysis.py",
    "bolt analysis/elastic_vs_icr_analysis.py",
    "bolt check/bearing_vs_slip_check.py",
    "bolt plotting/bolt_plotting_demo.py",
]


def main() -> None:
    print("=" * 60)
    print("RUNNING BOLT EXAMPLES")
    print("=" * 60)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{examples_dir};{src_dir}"

    for example in bolt_examples:
        print(f"\n{'─' * 60}")
        print(f"Running: {example}")
        print("─" * 60)

        result = subprocess.run([
            sys.executable,
            str(examples_dir / example),
        ], env=env, capture_output=False)

        if result.returncode != 0:
            print(f"❌ {example} failed!")
        else:
            print(f"✓ {example} completed")

    print("\n" + "=" * 60)
    print("BOLT EXAMPLES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
