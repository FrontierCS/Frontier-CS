from pymoo.core.crossover import Crossover
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.crossover.ux import UX
from pymoo.operators.crossover.ox import OrderCrossover
from pymoo.operators.repair.rounding import RoundingRepair
from utils.debug import *
import numpy as np


class DummyCrossover(Crossover):
    def __init__(self, args):
        super().__init__(2, 2, prob=0.9)
    
    def _do(self, problem, X, **kwargs):
        return X
    

###################################################################
#  Grid Guide crossover
###################################################################

class GuidGuideSBXCrossover(SBX):
    def __init__(self, args):
        super().__init__(
            repair=RoundingRepair(),
            prob=args.sbx_prob, eta=args.sbx_eta
        )

class MaskGuidedOptimizationUniformCrossover(UX):
    def __init__(self, args):
        super(MaskGuidedOptimizationUniformCrossover, self).__init__()
        self.args = args

###################################################################
#  SP crossover
###################################################################

class SPOrderCrossover(OrderCrossover):
    def __init__(self, args):
        super(SPOrderCrossover, self).__init__(shift=False)
        self.args = args
    
    def _do(self, problem, X, **kwargs):
        _, _, n_var = X.shape
        node_cnt = n_var // 2
        X1 = X[:, :, :node_cnt]
        X2 = X[:, :, node_cnt:]
        
        X1 = super(SPOrderCrossover, self)._do(problem=problem, X=X1)
        X2 = super(SPOrderCrossover, self)._do(problem=problem, X=X2)

        X = np.concatenate([X1, X2], axis=-1)
        return X

###################################################################
#  Hyperparameter crossover
###################################################################

class HyperparameterUniformCrossover(UX):
    def __init__(self, args):
        super(
            HyperparameterUniformCrossover, self
        ).__init__()
        self.args = args
    
