"""
Generate all gallery images by running examples.
"""
import sys
from pathlib import Path

# Add src directory to path so connecty can be imported
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Import and run each example
examples = [
    ("example1_rhs_simple", "Simple RHS with vertical load"),
    ("example2_rhs_eccentric", "RHS with eccentric load and torsion"),
    ("example3_i_beam", "I-beam with selective welding"),
    ("example4_u_channel", "U-channel with combined loading"),
    ("example5_stress_components", "Stress component breakdown"),
    ("example6_chs", "Circular hollow section"),
]

print("Generating gallery images...\n")

for module_name, description in examples:
    print(f"Running {module_name}: {description}")
    try:
        # Import the module
        module = __import__(module_name, fromlist=[''])
        print(f"✓ {module_name} completed\n")
    except Exception as e:
        print(f"✗ {module_name} failed: {e}\n")
        import traceback
        traceback.print_exc()

print("Gallery generation complete!")
print(f"\nCheck the gallery/ directory for SVG files.")

