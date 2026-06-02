from pymoo.core.problem import Problem
import numpy as np 
import ray
import sys

from utils.debug import *
import os 

class PlacementProblem(Problem):
    def __init__(self, n_var, xl, xu, placer):
        super().__init__(
            n_var=n_var,
            xl=xl,
            xu=xu,
            n_obj=1,
            vtype=np.int64
        )
        self.placer = placer 

    
    def _evaluate(self, x, out, *args, **kwargs):
        y, overlap_rate, macro_pos = self.placer.evaluate(x)
            
        out["F"] = np.array(y)
        out["overlap_rate"] = np.array(overlap_rate)
        out["macro_pos"] = macro_pos
        
class MaskGuidedOptimizationPlacementProblem(PlacementProblem):
    def __init__(self, n_grid_x, n_grid_y, placer):
        self.node_cnt = placer.placedb.node_cnt
        self.n_grid_x = n_grid_x
        self.n_grid_y = n_grid_y
        super().__init__(
            n_var=self.node_cnt * 2,
            xl=np.zeros(self.node_cnt * 2),
            xu=np.array(
                ([self.n_grid_x] * self.node_cnt) + \
                    ([self.n_grid_y] * self.node_cnt)
            ),
            placer=placer
        )
        
class SequencePairPlacementProblem(PlacementProblem):
    def __init__(self, placer):
        self.node_cnt = placer.placedb.node_cnt
        super().__init__(
            n_var=self.node_cnt * 2,
            xl=np.zeros(self.node_cnt * 2),
            xu=np.array([self.node_cnt] * self.node_cnt * 2),
            placer=placer
        )
        

class HyperparameterPlacementProblem(PlacementProblem):
    def __init__(self, params_space, placer):
        self.params_space = params_space
        self.n_var = len(self.params_space.keys())

        extract = lambda ent_i: \
            [entry[ent_i] for entry in self.params_space.values()]
        self.params_name = list(self.params_space.keys())
        self.xl = np.array(extract(0))
        self.xu = np.array(extract(1))

        super().__init__(
            n_var=self.n_var,
            xl=self.xl,
            xu=self.xu,
            placer=placer
        )