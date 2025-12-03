
"""
Verification script for Elastic vs ICR method comparison.
"""
from sectiony.library import rhs
from weldy import Weld, WeldParameters, Force
import math

def run_comparison(case_name: str, weld: Weld, force: Force):
    print(f"\n{case_name.upper()}")
    print("-" * 60)
    
    # Calculate
    elastic = weld.stress(force, method="elastic", discretization=200)
    icr = weld.stress(force, method="icr", discretization=200)
    
    # Metrics
    e_max = elastic.max
    i_max = icr.max
    
    e_util = elastic.utilization()
    i_util = icr.utilization()
    
    print(f"{'Metric':<15} | {'Elastic':<10} | {'ICR':<10} | {'Diff'}")
    print("-" * 60)
    print(f"{'Max Stress':<15} | {e_max:<10.1f} | {i_max:<10.1f} | {i_max/e_max - 1.0:>+6.1%}")
    print(f"{'Utilization':<15} | {e_util:<10.3%} | {i_util:<10.3%} | {i_util/e_util - 1.0:>+6.1%}")
    
    benefit = (e_util / i_util) - 1.0
    print(f"Capacity Benefit: {benefit:>+6.1%}")
    
    if icr.icr_point:
        print(f"ICR Point: ({icr.icr_point[0]:.1f}, {icr.icr_point[1]:.1f})")
        
    return benefit > 0

def verify_all():
    print("=" * 60)
    print("ICR vs ELASTIC VERIFICATION")
    print("=" * 60)
    
    # Setup
    section = rhs(b=100, h=200, t=10, r=15)
    params = WeldParameters(weld_type="fillet", leg=6.0, electrode="E70")
    weld = Weld.from_section(section=section, parameters=params)
    
    # Case 1: Pure Shear (Vertical)
    # Should show benefit due to theta-strength increase
    f1 = Force(Fy=-100000, location=(0, 0))
    res1 = run_comparison("Pure Shear (Concentric)", weld, f1)
    
    # Case 2: Eccentric Shear (Moderate)
    # e = 50mm (half width)
    f2 = Force(Fy=-100000, location=(0, 50))
    res2 = run_comparison("Eccentric Shear (e=50mm)", weld, f2)
    
    # Case 3: Eccentric Shear (Large)
    # e = 200mm
    f3 = Force(Fy=-100000, location=(0, 200))
    res3 = run_comparison("Eccentric Shear (e=200mm)", weld, f3)
    
    print("\n" + "=" * 60)
    if res1:
        print("PURE SHEAR: PASS (ICR > Elastic)")
    else:
        print("PURE SHEAR: FAIL (ICR < Elastic)")
        
    if res2:
        print("ECCENTRIC: PASS (ICR > Elastic)")
    else:
        print("ECCENTRIC: FAIL (ICR < Elastic)")

if __name__ == "__main__":
    verify_all()
