This is how welding should be implemented.

To make a weld you need a geometry and parameters.
## Geometry
The geometry should simply come from the setiony geomtry object which should have methods likke from_section, from_dxf and from_contours?
- check sectiony
- geometries should ahve a length attribute which is the total length of the geometry.

## WeldParams
The parameters are as follows
type: fillet, pjp, cjp, plug, slot
electrode: E60, E70, E80, E90, E100, E110
leg: float | None = None
throat:

this should have a capacioty that is calculated
weldparemeters.strength

## Weld
From the WeldParams and Geometry a Weld object is created.
tis has the attibutes area - which is calculated from the geometry and parameters.
also has centoid
and second moments of area about the centroid.

## Load
Load is anobject that has the attributes:
Fx, Fy, Fz, Mx, My, Mz
and a location attribute which is a tuple of the x,y and z coordinates of the load.
at the moment it might be called force and might be in force,py but this is wrong as ther are moments as well.

the method here is at(x,y,z) where it finds the equivalent force and moments at that point.

## LoadedWeld
LoadedWeld object is created with a force and a weld
it has methods of plotting and .icr and .elastic methods to calculate properties of the weld.

## LoadedWeldResult
when you apply a method to a loaded weld you get a LoadedWeldResult object.
if it is a fillet weld the default method is "both" which means it will return both the icr and elastic results.
fi the type is not icr then the method is "elastic" by default.

if method is both or icr you get these attributes:
icr_max_stress - maximum stress in the weld using the icr method
icr_max_stress_pos - position of the max stress using the icr method
icr_utilization - utilization of the weld using the icr method
icr_location - position of the instantaneous center of rotation using the icr method

if the method is elastic or bothyou get these attributes:
elastic_max_stress - maximum stress in the weld using the elastic method
elastic_max_stress_pos - position of the max stress using the elastic method
elastic_utilization - utilization of the weld using the elastic method




