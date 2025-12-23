"""
Run all connecty examples.
"""
import subprocess
import sys
from pathlib import Path

examples_dir = Path(__file__).parent

examples = [
    "weld analysis/standard_sections_analysis.py",
    "weld plotting/weld_method_comparison.py",
    "weld analysis/stress_components_analysis.py",
    "weld analysis/good_example.py",
    "weld plotting/icr_rotation_eccentricity_trend.py",
    "weld analysis/pjp_weld_analysis.py",
    "bolt analysis/bolt_group_analysis.py",
    "bolt analysis/elastic_vs_icr_analysis.py",
    "bolt check/bearing_vs_slip_check.py",
    "bolt plotting/bolt_plotting_demo.py",
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
