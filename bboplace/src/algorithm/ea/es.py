import cma 
import ray
import pickle 
import numpy as np 
import logging
from utils.debug import * 
from utils.constant import INF 
from utils.random_parser import set_state
from placer.hpo_placer import params_space
from ..basic_algo import BasicAlgo
from problem.pymoo_problem import (
    MaskGuidedOptimizationPlacementProblem,
    SequencePairPlacementProblem,
    HyperparameterPlacementProblem
)
import time 
import os 

from operators import REGISTRY as OPS_REGISTRY


class ES(BasicAlgo):
    def __init__(self, args, placer, logger):
        super(ES, self).__init__(args=args, placer=placer, logger=logger)
        self.node_cnt = placer.placedb.node_cnt
        self.best_hpwl = INF 
        
        if args.placer == "mgo":
            self.problem = MaskGuidedOptimizationPlacementProblem(
                n_grid_x=args.n_grid_x,
                n_grid_y=args.n_grid_y,
                placer=placer
            )
            self.xl = np.zeros(self.node_cnt * 2)
            self.xu = np.array(
                ([args.n_grid_x] * self.node_cnt) + \
                    ([args.n_grid_y] * self.node_cnt)
            )
        elif args.placer == "sp":
            self.xl = np.zeros(self.node_cnt * 2)
            self.xu = np.array([self.node_cnt] * self.node_cnt * 2)
            self.problem = SequencePairPlacementProblem(
                placer=placer
            )
        elif args.placer == "hpo":
            extract = lambda ent_i: \
                [entry[ent_i] for entry in params_space.values()]
            self.xl = np.array(extract(0))
            self.xu = np.array(extract(1))
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
        self.t = time.time() 
        
        checkpoint = self._load_checkpoint()
        if checkpoint is not None:
            self.cmaes = checkpoint["obj"]
        else:
            x_init = OPS_REGISTRY["sampling"][self.args.placer]["random"](self.args, self.placer) \
                    .do(self.problem, 1).get("X")
            self.cmaes = cma.CMAEvolutionStrategy(
                x_init, 
                self.args.sigma,
                {
                    "popsize": self.args.pop_size,
                    "bounds": [self.xl, self.xu],
                    "seed": self.args.seed
                }
            )
        
        def round_to_discrete(x):
            return np.round(x).astype(int)
        
        while self.n_eval < self.args.max_evals:
            population = self.cmaes.ask()
            fitness = [] 
            overlap_rate = []
            macro_pos_all = []
            
            if self.args.placer == "mgo":
                processed_population = [round_to_discrete(x) for x in population]
            elif self.args.placer == "sp":
                raise ValueError("CMA-ES is not supported for SP")
            elif self.args.placer == "hpo":
                processed_population = population

            fitness, overlap_rate, macro_pos_all = self.placer.evaluate(processed_population)
            
                
            t_temp = time.time() 
            t_eval = t_temp - self.t 
            self.t_total += t_eval
            t_each_eval = t_eval / self.args.pop_size 
            avg_t_each_eval = self.t_total / (self.n_eval + self.args.pop_size)
            avg_t_eval_solution = self.placer.t_eval_solution_total / (self.n_eval + self.args.pop_size)
            self.t = t_temp
            
            self._record_results(np.array(fitness), np.array(overlap_rate), macro_pos_all,
                                t_each_eval=t_each_eval,
                                avg_t_each_eval=avg_t_each_eval,
                                avg_t_eval_solution=avg_t_eval_solution)
            
            self._save_checkpoint() 
                
            

    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            super()._load_checkpoint()
            with open(os.path.join(self.args.checkpoint, "cma_es.pkl"), "rb") as f:
                checkpoint = pickle.load(f)
                self.start_from_checkpoint = True
        else:
                checkpoint = None
                self.start_from_checkpoint = False
        
        return checkpoint
    

    
    def _save_checkpoint(self):
        super()._save_checkpoint()

        with open(os.path.join(self.checkpoint_path, "cma_es.pkl"), "wb") as f:
            pickle.dump(
                {
                    "obj" : self.cmaes,
                },
                file=f
            )
        
