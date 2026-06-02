
REGISTRY = {}

# from .grid_placer import GridPlacer
from .mgo_placer import MaskGuidedOptimizationPlacer
from .sp_placer import SPPlacer
from .hpo_placer import HPOPlacer

# REGISTRY["grid"] = GridPlacer
REGISTRY["mgo"] = MaskGuidedOptimizationPlacer
REGISTRY["sp"] = SPPlacer
REGISTRY["hpo"] = HPOPlacer