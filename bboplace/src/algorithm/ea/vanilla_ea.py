from problem.pymoo_problem import MaskGuidedOptimizationPlacementProblem, SequencePairPlacementProblem, HyperparameterPlacementProblem
import numpy as np 
from utils.debug import * 
from utils.constant import INF
from pymoo.core.population import Population
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.optimize import minimize
from placer.hpo_placer import params_space
from ..basic_algo import BasicAlgo
import time
import os
import pickle

from operators import REGISTRY as OPS_REGISTRY

class VanillaEA(BasicAlgo):
    def __init__(self, args, placer, logger):
        super(VanillaEA, self).__init__(args=args, placer=placer, logger=logger)
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
        if checkpoint is not None:
            assert len(checkpoint["population"]) == self.args.n_population
            sampling = Population.new(X=checkpoint["population"], F=checkpoint["fitness"])
            algo_n_gen = checkpoint["n_gen"] - 1
        else:
            sampling = OPS_REGISTRY["sampling"][self.args.placer][self.args.sampling.lower()](self.args, self.placer)
            algo_n_gen = 0

        self._algo = GA(
            pop_size=self.args.n_population,
            sampling=sampling,
            crossover=OPS_REGISTRY["crossover"][self.args.placer][self.args.crossover.lower()](self.args),
            mutation=OPS_REGISTRY["mutation"][self.args.placer][self.args.mutation.lower()](self.args),
            callback=self._save_callback,
            eliminate_duplicates=True
        )

            
        self.t = time.time()

        max_n_gen = self.args.max_evals // self.args.n_population - \
                self.args.n_sampling_repeat + 1
        res = minimize(
            problem=self.problem,
            algorithm=self._algo,
            termination=('n_gen', max_n_gen - algo_n_gen),
            verbose=True
        )


    def _save_callback(self, algo):
        # compute time
        t_temp = time.time()
        t_eval = t_temp - self.t
        self.t_total += t_eval
        t_each_eval = t_eval / self.args.n_population
        avg_t_each_eval = self.t_total / (self.n_eval + self.args.n_population * 2)
        avg_t_eval_solution = self.placer.t_eval_solution_total / (self.n_eval + self.args.n_population * 2)
        self.t = t_temp

        macro_pos_all = algo.pop.get("macro_pos")
        overlap_rate = algo.pop.get("overlap_rate")
        hpwl = algo.pop.get("F").flatten()

        if not self.start_from_checkpoint:
            self._record_results(hpwl=hpwl, 
                                 overlap_rate=overlap_rate,
                                 macro_pos_all=macro_pos_all,
                                 t_each_eval=t_each_eval, 
                                 avg_t_each_eval=avg_t_each_eval,
                                 avg_t_eval_solution=avg_t_eval_solution)
        else:
            self.start_from_checkpoint = False


        self._save_checkpoint(
            population=algo.pop.get("X"),
            fitness=algo.pop.get("F"),
            n_gen=self._algo.n_gen 
        )

        # assert0(algo.pop[0].evaluated)

    def _save_checkpoint(self, population, fitness, n_gen):
        super()._save_checkpoint()

        with open(os.path.join(self.checkpoint_path, "ea.pkl"), "wb") as f:
            pickle.dump(
                {
                    "population" : population,
                    "fitness" : fitness,
                    "n_gen" : n_gen
                },
                file=f
            )
        
    
    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            super()._load_checkpoint()
            with open(os.path.join(self.args.checkpoint, "ea.pkl"), "rb") as f:
                checkpoint = pickle.load(f)
                self.start_from_checkpoint = True
        else:
                checkpoint = None
                self.start_from_checkpoint = False
        
        return checkpoint
