"""
Run all connecty examples.
"""
import subprocess
import sys
from pathlib import Path

examples_dir = Path(__file__).parent

examples = [
    "standard_sections_analysis.py",
    "weld_method_comparison.py",
    "stress_components_analysis.py",
    "bolt_group_analysis.py",
    "good example.py",
    "icr_rotation_eccentricity_trend.py",
    "pjp_weld_analysis.py",
]

print("=" * 60)
print("RUNNING ALL CONNECTY EXAMPLES")
print("=" * 60)

for example in examples:
    print(f"\n{'─' * 60}")
    print(f"Running: {example}")
    print("─" * 60)
    
    # Run example with examples dir in PYTHONPATH so common imports work
    env = {"PYTHONPATH": str(examples_dir) + ";" + str(examples_dir.parent / "src")}
    
    # Merge with current environment
    import os
    current_env = os.environ.copy()
    current_env.update(env)

    result = subprocess.run(
        [sys.executable, str(examples_dir / example)],
        capture_output=False,
        env=current_env
    )
    
    if result.returncode != 0:
        print(f"❌ {example} failed!")
    else:
        print(f"✓ {example} completed")

print("\n" + "=" * 60)
print("ALL EXAMPLES COMPLETE")
print("=" * 60)
