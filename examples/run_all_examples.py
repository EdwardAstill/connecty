"""
Run all examples and generate gallery images.
"""
import sys
import subprocess
from pathlib import Path

# Get project root (parent of examples directory)
examples_dir = Path(__file__).parent
project_root = examples_dir.parent

examples = [
    "example1_rhs_simple",
    "example2_rhs_eccentric",
    "example3_i_beam",
    "example4_u_channel",
    "example5_stress_components",
    "example6_chs",
]

print("Running all examples...\n")

# Use uv run to ensure package is available
for example_name in examples:
    print(f"Running {example_name}...")
    try:
        # Run each example using uv run from project root
        example_path = examples_dir / f"{example_name}.py"
        result = subprocess.run(
            ["uv", "run", "python", str(example_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ {example_name} completed")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"✗ {example_name} failed:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
        print()
    except Exception as e:
        print(f"✗ {example_name} failed: {e}\n")

print("All examples completed!")

