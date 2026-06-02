from pymoo.core.sampling import Sampling
from pymoo.operators.sampling.rnd import IntegerRandomSampling, PermutationRandomSampling
from abc import abstractmethod
from copy import deepcopy
from utils.debug import *
import numpy as np
import math
import ray 
import os 


class BasicSampling():
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        self.args = args
        self.placer = placer

        if n_repeat is None:
            self.n_repeat = self.args.n_sampling_repeat
        else:
            self.n_repeat = n_repeat
    
    def _do(self, problem, n_samples, **kwargs):

        X, y_all, overlap_rate, macro_pos_all = self._sampling_do(problem=problem,
                                                n_samples=n_samples * self.n_repeat,
                                                kwargs=kwargs)
        sorted_indices = np.argsort(y_all)
        if self.n_repeat > 1:
            self.args.record_func(
                hpwl=y_all[sorted_indices[n_samples:]], 
                overlap_rate=overlap_rate[sorted_indices[n_samples:]],
                macro_pos_all=list(np.array(macro_pos_all)[sorted_indices[n_samples:]])
            ) 
        return X[sorted_indices[:n_samples]]

    
    @abstractmethod
    def _sampling_do(self, problem, n_samples, **kwargs):
        pass

###################################################################
#  Grid Guide sampling
###################################################################

class GrideGuideSingleRandomSampling(BasicSampling, IntegerRandomSampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        BasicSampling.__init__(self, args=args, placer=placer, use_checkpoint=use_checkpoint, n_repeat=n_repeat)
        IntegerRandomSampling.__init__(self)
        self.args = args 
        self.placer = placer
    
    def _sampling_do(self, problem, n_samples, **kwargs):
        return IntegerRandomSampling.do(
            self,
            problem=problem,
            n_samples=n_samples,
            kwargs=kwargs
        )


class GrideGuideRandomSampling(BasicSampling, IntegerRandomSampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        BasicSampling.__init__(self, args=args, placer=placer, use_checkpoint=use_checkpoint, n_repeat=n_repeat)
        IntegerRandomSampling.__init__(self)
        self.args = args 
        self.placer = placer 
    
    def _sampling_do(self, problem, n_samples, **kwargs):
        x = IntegerRandomSampling._do(self, problem, n_samples, **kwargs)
        y, overlap_rate, macro_pos = self.placer.evaluate(x)
        y = np.array(y)
        overlap_rate = np.array(overlap_rate)
        return x, y, overlap_rate, macro_pos

    
class GrideGuideSpiralSampling(BasicSampling, Sampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        BasicSampling.__init__(self, args=args, placer=placer, use_checkpoint=use_checkpoint, n_repeat=n_repeat)
        Sampling.__init__(self)
        self.args = args
        self.placer = placer
        self.n_grid_x = args.n_grid_x
        self.n_grid_y = args.n_grid_y

        self.macro_lst = placer.placedb.macro_lst
        self.node_info = placer.placedb.node_info
    
    def _get_position_mask(self, placed_macro, size_x, size_y):
        position_mask = np.zeros(shape=(self.n_grid_x, self.n_grid_y))
        for macro in placed_macro:
            start_x = max(0, placed_macro[macro][0] - size_x + 1)
            start_y = max(0, placed_macro[macro][1] - size_y + 1)
            end_x = min(placed_macro[macro][0] + placed_macro[macro][2] - 1, self.n_grid_x)
            end_y = min(placed_macro[macro][1] + placed_macro[macro][3] - 1, self.n_grid_y)
            position_mask[start_x: end_x + 1, start_y: end_y + 1] = 1
        position_mask[self.n_grid_x - size_x + 1:, :] = 1
        position_mask[:, self.n_grid_y - size_y + 1:] = 1

        return position_mask
    
    def _sampling_do(self, problem, n_samples, **kwargs):
        assert n_samples == 1 # only for n_pop = 1

        # get spiral grids for placement
        grid_id_lst = []
        visited_flag = [False for _ in range(self.n_grid_x * self.n_grid_y)]
        dir_row = [0, 1, 0, -1]
        dir_col = [1, 0, -1, 0]
        row_id = 0
        col_id = 0
        dir_id = 0
        for _ in range(self.n_grid_x * self.n_grid_y):
            grid_id = row_id * self.n_grid_y + col_id
            grid_id_lst.append(grid_id)
            visited_flag[grid_id] = True
            next_row = row_id + dir_row[dir_id]
            next_col = col_id + dir_col[dir_id]
            next_grid_id = next_row * self.n_grid_y + next_col
            if (0 <= next_row < self.n_grid_x) and \
               (0 <= next_col < self.n_grid_y) and \
               not visited_flag[next_grid_id]:
                row_id = next_row
                col_id = next_col
            else:
                dir_id = (dir_id + 1) % 4
                row_id += dir_row[dir_id]
                col_id += dir_col[dir_id]
        
        # sort macro besed on area
        sort_macros_map = {}
        for macro in self.macro_lst:
            sort_macros_map[macro] = self.node_info[macro]["size_x"] * self.node_info[macro]["size_y"]
        sort_macros = [k for k, v in sorted(sort_macros_map.items(), key = lambda item: item[1], reverse = True)]

        # init placement
        placed_macro = {}
        for macro in sort_macros:
            size_x, size_y = self.node_info[macro]["size_x"], self.node_info[macro]["size_y"]
            scale_size_x = math.ceil(size_x / self.placer.grid_width)
            scale_size_y = math.ceil(size_y / self.placer.grid_height)
            position_mask = self._get_position_mask(placed_macro, scale_size_x, scale_size_y)
            for grid_id in grid_id_lst:
                grid_id_x = grid_id // self.n_grid_y
                grid_id_y = grid_id %  self.n_grid_y
                if position_mask[grid_id_x, grid_id_y] == 1:
                    continue
                
                placed_macro[macro] = (grid_id_x, grid_id_y, scale_size_x, scale_size_y)
                break
        
        node_cnt = problem.n_var // 2
        assert len(placed_macro) == node_cnt 
        assert len(sort_macros) == node_cnt

        # get X
        X = np.zeros(shape=(n_samples, problem.n_var))
        for i, macro in enumerate(self.macro_lst):
            pos_x, pos_y, _, _ = placed_macro[macro]
            X[0, i], X[0, i + node_cnt] = pos_x, pos_y
        
        
        y, overlap_rate, macro_pos = self.placer.evaluate(X)
        
        y = np.array(y)
        overlap_rate = np.array([overlap_rate[0]])
        return X, y, overlap_rate, macro_pos


###################################################################
#  SP sampling
###################################################################

class _SPRandomSampling(PermutationRandomSampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        super(_SPRandomSampling, self).__init__()
        self.args = args
        self.placer = placer
    
    def _do(self, problem, n_samples, **kwargs):
        sub_n_var = problem.n_var // 2
        sub_xl = problem.xl[:sub_n_var]
        sub_xu = problem.xu[:sub_n_var]
        sub_problem = deepcopy(problem)
        sub_problem.n_var = sub_n_var
        sub_problem.xl = sub_xl
        sub_problem.xu = sub_xu
        X1 = PermutationRandomSampling._do(self, problem=sub_problem, 
                                               n_samples=n_samples)
        X2 = PermutationRandomSampling._do(self, problem=sub_problem, 
                                               n_samples=n_samples)
        X = np.concatenate([X1, X2], axis=1)
        return X
    
class SPRandomSampling(BasicSampling, _SPRandomSampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        BasicSampling.__init__(self, args=args, placer=placer, use_checkpoint=use_checkpoint, n_repeat=n_repeat)
        _SPRandomSampling.__init__(self, args=args, placer=placer)
    
    def _sampling_do(self, problem, n_samples, **kwargs):
        x = _SPRandomSampling._do(self, problem, n_samples, **kwargs)
        y, overlap_rate, macro_pos = self.placer.evaluate(x)
        y = np.array(y)    
        overlap_rate = np.array(overlap_rate) 
        return x, y, overlap_rate, macro_pos
    
###################################################################
#  Hyperparameter sampling
###################################################################
class HyperparameterSampling(BasicSampling, Sampling):
    def __init__(self, args, placer, use_checkpoint=True, n_repeat=None) -> None:
        BasicSampling.__init__(self, args=args, placer=placer, use_checkpoint=use_checkpoint, n_repeat=n_repeat)
        Sampling.__init__(self)

    def _sampling_do(self, problem, n_samples, **kwargs):
        xl, xu = problem.xl, problem.xu
        xd = xu - xl
        n_var = problem.n_var

        X = np.dot(np.random.uniform(size=(n_samples, n_var)), np.diag(xd)) + xl

        y, overlap_rate, macro_pos = self.placer.evaluate(X)

        y = np.array(y)
        overlap_rate = np.array(overlap_rate)
        return X, y, overlap_rate, macro_pos