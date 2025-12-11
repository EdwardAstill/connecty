"""
Generate all gallery images by running examples.
"""
import sys
from pathlib import Path

# Add src directory to path so connecty can be imported
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

print("=" * 60)
print("CONNECTY GALLERY GENERATION")
print("=" * 60)

# Import and run each example module
example_modules = [
    ("standard_sections_analysis", "Standard sections with various loads"),
    ("weld_method_comparison", "Elastic vs ICR method comparison"),
    ("stress_components_analysis", "Detailed stress component breakdown"),
    ("icr_rotation_eccentricity_trend", "ICR rotation with eccentricity"),
    ("pjp_weld_analysis", "PJP weld analysis example"),
    ("good example", "Eccentrically loaded RHS with ICR"),
    ("bolt_group_analysis", "Bolt group force analysis"),
]

print()

for module_name, description in example_modules:
    print(f"Running: {description}")
    print(f"  Module: {module_name}")
    try:
        # Import the module
        module = __import__(module_name, fromlist=['run'])
        
        # Run if it has a run() function
        if hasattr(module, 'run'):
            module.run()
        elif hasattr(module, 'main'):
            module.main()
        
        print(f"  ✓ Completed\n")
    except Exception as e:
        print(f"  ✗ Failed: {e}\n")
        import traceback
        traceback.print_exc()

print("=" * 60)
print("Gallery generation complete!")
print("Check the gallery/ directory for SVG files.")
print("=" * 60)
