from pymoo.core.mutation import Mutation
from pymoo.operators.mutation.pm import PM
from pymoo.operators.mutation.inversion import InversionMutation
from pymoo.operators.repair.rounding import RoundingRepair
from utils.constant import EPS
import numpy as np
import random
from utils.debug import *



class DummyMutation(Mutation):
    def __init__(self,args) -> None:
        self.args = args
        super(MaskGuidedOptimizationSwapMutation, self).__init__(prob=1, prob_var=None)
    
    def _do(self, problem, X, **kwargs):
        return X

###################################################################
#  Grid Guide mutation
###################################################################

class MaskGuidedOptimizationPMMutation(PM):
    def __init__(self, args):
        super().__init__(
            repair=RoundingRepair(),
            prob=args.pm_prob, eta=args.pm_eta
        )

class MaskGuidedOptimizationSwapMutation(Mutation):
    def __init__(self,args) -> None:
        self.args = args
        super(MaskGuidedOptimizationSwapMutation, self).__init__(prob=1, prob_var=None)

    def _do(self, problem, X, **kwargs):
        node_cnt = X.shape[1] // 2
        idx = np.random.choice(node_cnt, size=(X.shape[0], 2), replace=False)
        
        X_swapped = X.copy()
        X_swapped[:, idx[:, 0]], X_swapped[:, idx[:, 1]] = \
            X[:, idx[:, 1]], X[:, idx[:, 0]]
        X_swapped[:, idx[:, 0] + node_cnt], X_swapped[:, idx[:, 1] + node_cnt] = \
            X[:, idx[:, 1] + node_cnt], X[:, idx[:, 0] + node_cnt]
        
        return X_swapped

class MaskGuidedOptimizationShiftMutation(Mutation):
    def __init__(self, args) -> None:
        self.args = args
        super(MaskGuidedOptimizationShiftMutation, self).__init__(prob=1, prob_var=None)
    
    def _do(self, problem, X, **kwargs):
        node_cnt = X.shape[1] // 2
        direction_lst = [(1,0), (-1,0), (0,1), (0,-1)]
        for id in range(X.shape[0]):
            idx = np.random.choice(list(range(node_cnt)), size=1, replace=False)[0]
            while True:
                direction_id = np.random.choice(list(range(4)), size=1, replace=False)[0]
                direction = direction_lst[direction_id]
                if 0 <= X[id][idx] + direction[0] < self.args.n_grid_x \
                   and 0 <= X[id][idx+node_cnt] + direction[1] < self.args.n_grid_y:
                    X[id][idx]          += direction[0]
                    X[id][idx+node_cnt] += direction[1]
                    break
        return X
    
class MaskGuidedOptimizationRandomResettingMutation(Mutation):
    def __init__(self, args) -> None:
        self.args = args
        super(MaskGuidedOptimizationRandomResettingMutation, self).__init__(prob=1, prob_var=None)

    def _do(self, problem, X, **kwargs):
        node_cnt = X.shape[1] // 2
        for id in range(X.shape[0]):
            idx = np.random.choice(list(range(node_cnt)), size=1, replace=False)[0]
            X[id][idx]            = np.random.randint(low=0, high=self.args.n_grid_x)
            X[id][idx + node_cnt] = np.random.randint(low=0, high=self.args.n_grid_y)
        return X
    
class MaskGuidedOptimizationShuffleMutation(Mutation):
    def __init__(self, args) -> None:
        self.args = args
        super(MaskGuidedOptimizationShuffleMutation, self).__init__(prob=1, prob_var=None)
    
    def _do(self, problem, X, **kwargs):
        node_cnt = X.shape[1] // 2
        _X = X.copy()
        for id in range(X.shape[0]):
            chosen_idx   = np.random.choice(list(range(node_cnt)), size=4, replace=False)
            shuffled_idx = chosen_idx.copy()
            np.random.shuffle(shuffled_idx)
            for origin_idx, target_idx in zip(chosen_idx, shuffled_idx):
                _X[id][origin_idx], _X[id][origin_idx + node_cnt] = X[id][target_idx], X[id][target_idx + node_cnt]
        
        return _X
    

###################################################################
#  SP mutation
###################################################################

class SPInversionMutation(InversionMutation):
    def __init__(self, args):
        super(SPInversionMutation, self).__init__(prob=1.0)
        self.args = args

    def _do(self, problem, X, **kwargs):
        node_cnt = X.shape[1] // 2
        X1 = X[:, :node_cnt]
        X2 = X[:, node_cnt:]
        assert X1.shape == X2.shape
        X1 = super(SPInversionMutation, self)._do(problem, X1)
        X2 = super(SPInversionMutation, self)._do(problem, X2)
        X = np.concatenate([X1, X2], axis=1)
        return X
    
###################################################################
#  Hyperparameter mutation
###################################################################

class HyperparameterRandomResettingMutation(Mutation):
    def __init__(self, args) -> None:
        self.args = args
        super(
            HyperparameterRandomResettingMutation, self
        ).__init__(prob=1, prob_var=None)

    def _do(self, problem, X, **kwargs):
        params_space = [
            (idx, xl, xu)
            for idx, (xl, xu, _) in enumerate(problem.params_space.values())
        ]
        for x in X:
            idx, xl, xu = random.choice(params_space)
            x[idx] = np.random.uniform() * (xu - xl) + xl
        return X