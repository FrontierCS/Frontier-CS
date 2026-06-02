import time
import os
import pickle
from pypop7.optimizers.pso.pso import PSO as PYPSO
from pypop7.optimizers.core.optimizer import Optimizer
from problem.pso_problem import MaskGuidedOptimizationPlacementProblem, SequencePairPlacementProblem, HyperparameterPlacementProblem
import numpy as np 
import logging
from utils.debug import * 
from utils.constant import INF 
from placer.hpo_placer import params_space
from ..basic_algo import BasicAlgo

from operators import REGISTRY as OPS_REGISTRY

class Wrapped_PYPSO(PYPSO):
    def __init__(self, args, placer, problem, options):
        self.args = args
        self.placer = placer
        self.origin_problem = problem
        options["max_function_evaluations"] = args.max_evals - \
            ((args.n_sampling_repeat - 1) * args.n_population)
        super(Wrapped_PYPSO, self).__init__(
            problem=problem.get_problem_dict(),
            options=options
        )

    def initialize(self, args=None):
        macro_pos_lst = []
        v = self.rng_initialization.uniform(self._min_v, self._max_v, size=self._swarm_shape)  # velocities
        x = OPS_REGISTRY["sampling"][self.args.placer]["random"](self.args, self.placer) \
            .do(self.origin_problem, self.n_individuals).get("X").astype(np.float64)
        y = np.empty((self.n_individuals,))  # fitness
        overlap_rate = np.zeros((self.n_individuals, ))
        p_x, p_y = np.copy(x), np.copy(y)  # personally previous-best positions and fitness
        n_x = np.copy(x)  # neighborly previous-best positions

        for i in range(self.n_individuals):
            if self._check_terminations():
                return v, x, y, p_x, p_y, n_x
            y[i], overlap_rate[i], macro_pos = self._evaluate_fitness(x[i], args)
            macro_pos_lst.append(macro_pos)
        p_y = np.copy(y)
        return v, x, y, p_x, p_y, n_x, overlap_rate, macro_pos_lst
    
    def _evaluate_fitness(self, x, args=None):
        self.start_function_evaluations = time.time()
        if args is None:
            y, overlap_rate, macro_pos = self.fitness_function(x)
        else:
            y, overlap_rate, macro_pos = self.fitness_function(x, args=args)
        y = y[0]
        overlap_rate = overlap_rate[0]
        macro_pos = macro_pos[0]

        self.time_function_evaluations += time.time() - self.start_function_evaluations
        self.n_function_evaluations += 1
        # update best-so-far solution (x) and fitness (y)
        if y < self.best_so_far_y:
            self.best_so_far_x, self.best_so_far_y = np.copy(x), y
        # update all settings related to early stopping
        if (self._base_early_stopping - y) <= self.early_stopping_threshold:
            self._counter_early_stopping += 1
        else:
            self._counter_early_stopping, self._base_early_stopping = 0, y
        # highlight(float(y), float(overlap_rate))
        return float(y), float(overlap_rate), macro_pos
    
    def iterate(self, v=None, x=None, y=None, p_x=None, p_y=None, n_x=None, args=None):
        macro_pos_lst = []
        overlap_rate = np.zeros((self.n_individuals, ))
        for i in range(self.n_individuals):
            if self._check_terminations():
                return v, x, y, p_x, p_y, n_x, macro_pos_lst
            n_x[i] = p_x[np.argmin(p_y)]  # online update within global topology
            cognition_rand = self.rng_optimization.uniform(size=(self.ndim_problem,))
            society_rand = self.rng_optimization.uniform(size=(self.ndim_problem,))
            v[i] = (self._w[min(self._n_generations, len(self._w) - 1)]*v[i] +
                    self.cognition*cognition_rand*(p_x[i] - x[i]) +
                    self.society*society_rand*(n_x[i] - x[i]))  # velocity update
            v[i] = np.clip(v[i], self._min_v, self._max_v)
            x[i] += v[i]  # position update
            if self.is_bound:
                x[i] = np.clip(x[i], self.lower_boundary, self.upper_boundary)
            y[i], overlap_rate[i], macro_pos = self._evaluate_fitness(x[i], args)  # fitness evaluation
            macro_pos_lst.append(macro_pos)
            if y[i] < p_y[i]:  # online update
                p_x[i], p_y[i] = x[i], y[i]
        self._n_generations += 1
        return v, x, y, p_x, p_y, n_x, overlap_rate, macro_pos_lst

    
class PSO(BasicAlgo):
    def __init__(self, args, placer, logger):
        super(PSO, self).__init__(args=args, placer=placer, logger=logger)
        self.node_cnt = placer.placedb.node_cnt
        self.best_hpwl = INF
        
        if args.placer == "mgo":
            self.problem = MaskGuidedOptimizationPlacementProblem(
                n_grid_x=args.n_grid_x,
                n_grid_y=args.n_grid_y,
                placer=placer
            )
        elif args.placer == "sp":
            self.problem = SequencePairPlacementProblem(
                placer=placer
            )
        elif args.placer == "hpo":
            self.problem = HyperparameterPlacementProblem(
                params_space=params_space,
                placer=placer,
            )
        else:
            raise NotImplementedError

        self.args.__dict__.update(
            {"logger": logger, "record_func": self._record_results}
        )
    
    def run(self):
        checkpoint = self._load_checkpoint()
        self.pso = Wrapped_PYPSO(
            args=self.args, 
            placer=self.placer,
            problem=self.problem,
            options={
                "max_function_evaluations" : self.args.max_evals,
                "n_individuals" : self.args.n_population,
                "is_bound" : True,
            }
        )
        fitness = []
        self.pso.start_time = time.time()
        self.t = self.pso.start_time
        if checkpoint is not None:
            assert len(checkpoint["x"]) == self.args.n_population
            v = checkpoint["v"]
            x = checkpoint["x"]
            y = checkpoint["y"]
            p_x = checkpoint["p_x"]
            p_y = checkpoint["p_y"]
            n_x = checkpoint["n_x"]
            self.pso.n_function_evaluations = self.n_eval - \
                ((self.args.n_sampling_repeat - 1) * self.args.n_population)
            overlap_rate = None
            macro_pos_lst = None
        else:
            v, x, y, p_x, p_y, n_x, overlap_rate, macro_pos_lst = self.pso.initialize(args=None)
        self._save_callback(
            v=v,
            x=x,
            y=y,
            p_x=p_x,
            p_y=p_y,
            n_x=n_x,
            overlap_rate=overlap_rate,
            macro_pos_all=macro_pos_lst
        )
        while not self.pso.termination_signal:
            self.pso._print_verbose_info(fitness, y)
            v, x, y, p_x, p_y, n_x, overlap_rate, macro_pos_lst = self.pso.iterate(v, x, y, p_x, p_y, n_x, args=None)
            self._save_callback(
                v=v,
                x=x,
                y=y,
                p_x=p_x,
                p_y=p_y,
                n_x=n_x,
                overlap_rate=overlap_rate,
                macro_pos_all=macro_pos_lst
            )
        return self.pso._collect(fitness, y)
    
    def _save_callback(self, v, x, y, p_x, p_y, n_x, overlap_rate, macro_pos_all):
        # compute time
        t_temp = time.time()
        t_eval = t_temp - self.t
        self.t_total += t_eval
        t_each_eval = t_eval / self.args.n_population
        avg_t_each_eval = self.t_total / (self.n_eval + self.args.n_population * 2)
        avg_t_eval_solution = self.placer.t_eval_solution_total / (self.n_eval + self.args.n_population * 2)
        self.t = t_temp


        if not self.start_from_checkpoint:
            self._record_results(hpwl=y, 
                                 overlap_rate=overlap_rate,
                                 macro_pos_all=macro_pos_all,
                                 t_each_eval=t_each_eval, 
                                 avg_t_each_eval=avg_t_each_eval,
                                 avg_t_eval_solution=avg_t_eval_solution)
        else:
            self.start_from_checkpoint = False


        self._save_checkpoint(
            v=v,
            x=x,
            y=y,
            p_x=p_x,
            p_y=p_y,
            n_x=n_x
        )
    
    def _save_checkpoint(self, v, x, y, p_x, p_y, n_x):
        super()._save_checkpoint()

        with open(os.path.join(self.checkpoint_path, "pso.pkl"), "wb") as f:
            pickle.dump(
                {
                    "v" : v,
                    "x" : x,
                    "y" : y,
                    "p_x" : p_x,
                    "p_y" : p_y,
                    "n_x" : n_x
                },
                file=f
            )
    
    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            super()._load_checkpoint()
            with open(os.path.join(self.args.checkpoint, "pso.pkl"), "rb") as f:
                checkpoint = pickle.load(f)
                self.start_from_checkpoint = True
        else:
                checkpoint = None
                self.start_from_checkpoint = False
        
        return checkpoint
