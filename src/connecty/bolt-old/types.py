from typing import Literal, Tuple

Point2D = Tuple[float, float]
TensionMethod = Literal["conservative", "accurate"]
ShearMethod = Literal["elastic", "icr"]
HoleType = Literal["standard", "oversize", "short-slot", "long-slot"]
SurfaceClass = Literal["A", "B"]

