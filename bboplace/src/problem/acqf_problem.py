from pymoo.core.problem import Problem 
import torch 
import numpy as np
from utils.debug import *

tkwargs = {
    "dtype": torch.double,
    "device": torch.device("cuda" if torch.cuda.is_available() else "cpu")
}

class AcquisitionFuncProblem(Problem):
    def __init__(self, n_var, xl, xu, acqf):
        super().__init__(n_var=n_var, xl=xl, xu=xu, n_obj=1)
        self.acqf = acqf 
    
    def _evaluate(self, x, out, *args, **kwargs):
        # highlight(x.shape)
        if isinstance(x, (np.ndarray, list)):
            x = torch.tensor(x).to(**tkwargs)
        with torch.no_grad():
            out["F"] = self.acqf(x.unsqueeze(0)).reshape(-1, 1)\
                .detach().cpu().numpy() * (-1)
        torch.cuda.empty_cache()

class MaskGuidedOptimizationAcquisitionFuncProblem(AcquisitionFuncProblem):
    def __init__(self, n_grid_x, n_grid_y, node_cnt, acqf):
        self.n_grid_x = n_grid_x
        self.n_grid_y = n_grid_y
        self.node_cnt = node_cnt
        super().__init__(
            n_var=self.node_cnt * 2,
            xl=np.zeros(self.node_cnt * 2),
            xu=np.array(
                ([self.n_grid_x] * self.node_cnt) + \
                    ([self.n_grid_y] * self.node_cnt)
            ),
            acqf=acqf
        )
        
class SequencePairAcquisitionFuncProblem(AcquisitionFuncProblem):
    def __init__(self, node_cnt, acqf):
        self.node_cnt = node_cnt
        super().__init__(
            n_var=self.node_cnt * 2,
            xl=np.zeros(self.node_cnt * 2),
            xu=np.array([self.node_cnt] * self.node_cnt * 2),
            acqf=acqf
        )

class HyperparameterAcquisitionFuncProblem(AcquisitionFuncProblem):
    def __init__(self, params_space, acqf):
        self.params_space = params_space
        n_var = len(self.params_space.keys())

        extract = lambda ent_i: \
            [entry[ent_i] for entry in self.params_space.items()]
        
        self.xl = np.array(extract(0))
        self.xu = np.array(extract(1))

        super().__init__(
            n_var=n_var,
            xl=self.xl,
            xu=self.xu,
            acqf=acqf,
        )