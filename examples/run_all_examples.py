"""
Run all connecty examples.
"""
import subprocess
import sys
from pathlib import Path

examples_dir = Path(__file__).parent

examples = [
    "example1_rhs_simple.py",
    "example2_rhs_eccentric.py",
    "example3_i_beam.py",
    "example4_u_channel.py",
    "example5_stress_components.py",
    "example6_chs.py",
]

print("=" * 60)
print("RUNNING ALL CONNECTY EXAMPLES")
print("=" * 60)

for example in examples:
    print(f"\n{'─' * 60}")
    print(f"Running: {example}")
    print("─" * 60)
    
    result = subprocess.run(
        [sys.executable, str(examples_dir / example)],
        capture_output=False
    )
    
    if result.returncode != 0:
        print(f"❌ {example} failed!")
    else:
        print(f"✓ {example} completed")

print("\n" + "=" * 60)
print("ALL EXAMPLES COMPLETE")
print("=" * 60)
