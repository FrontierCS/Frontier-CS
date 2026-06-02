REGISTRY = {}

from .ea.vanilla_ea import VanillaEA
from .bo.bo import BO 
# from .bo.saasbo import SAASBO
from .sa.sa import SA
from .ea.es import ES
from .ea.pso import PSO
from .rs.rs import RS

REGISTRY["ea"] = VanillaEA
REGISTRY["bo"] = BO
# REGISTRY["saasbo"] = SAASBO
REGISTRY["sa"] = SA
REGISTRY["es"] = ES
REGISTRY["pso"] = PSO
REGISTRY["rs"] = RS

try:
    from .bo.saasbo import SAASBO
    REGISTRY["saasbo"] = SAASBO
except:
    pass