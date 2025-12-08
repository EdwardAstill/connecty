"""
Common geometry definitions for examples.
"""
from sectiony.library import rhs, i, chs, u
from connecty import Weld, WeldParams

# 1. Standard RHS with Fillet Weld
def get_rhs_weld():
    section = rhs(b=100, h=200, t=10, r=15)
    params = WeldParams(type="fillet", leg=6.0, electrode="E70")
    return Weld.from_section(section=section, parameters=params)

# 2. Wide RHS for Horizontal Stacking
def get_wide_rhs_weld():
    section = rhs(b=500, h=80, t=10, r=15)
    params = WeldParams(type="fillet", leg=6.0, electrode="E70")
    return Weld.from_section(section=section, parameters=params)

# 3. I-Beam with All-Around Fillet
def get_ibeam_weld():
    section = i(d=200, b=100, tf=10, tw=6, r=8)
    params = WeldParams(type="fillet", leg=8.0, electrode="E70")
    return Weld.from_section(section=section, parameters=params)

# 4. U-Channel (C-Section)
def get_channel_weld():
    section = u(h=200, b=75, t=10, r=8)
    params = WeldParams(type="fillet", leg=6.0, electrode="E70")
    return Weld.from_section(section=section, parameters=params)

# 5. Circular Hollow Section (CHS)
def get_chs_weld():
    section = chs(d=150, t=6.0)
    params = WeldParams(type="fillet", leg=5.0, electrode="E70")
    return Weld.from_section(section=section, parameters=params)

