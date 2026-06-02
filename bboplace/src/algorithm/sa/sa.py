from problem.pymoo_problem import MaskGuidedOptimizationPlacementProblem, SequencePairPlacementProblem, HyperparameterPlacementProblem
import numpy as np 
import pickle
import time
import os
from placer.hpo_placer import params_space
from utils.debug import * 
from utils.constant import INF
from ..basic_algo import BasicAlgo

from operators import REGISTRY as OPS_REGISTRY

class SA(BasicAlgo):
    def __init__(self, args, placer, logger):
        assert args.n_population == 1
        super(SA, self).__init__(args=args, placer=placer, logger=logger)
        self.node_cnt = placer.placedb.node_cnt

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

        
        self.decay = args.decay
        self.init_T = args.T 
        self.T = args.T 
        self.update_freq = args.update_freq
        self.max_evals = args.max_evals
        
        self.population = None
        self.population_hpwl = INF
        
        self.sampling = OPS_REGISTRY["sampling"][self.args.placer][self.args.sampling.lower()](self.args, self.placer)
        self.mutation = OPS_REGISTRY["mutation"][self.args.placer][self.args.mutation.lower()](self.args)
    
        self.args.__dict__.update(
            {"logger": logger, "record_func": self._record_results}
        )
        
    
    def run(self):
        checkpoint = self._load_checkpoint()
        if checkpoint is not None:
            self.T = checkpoint["temperature"]

        while self.n_eval < self.max_evals:
            t_start = time.time()
            if self.population is None:
                if checkpoint is None:
                    now_x = self.sampling.do(self.problem, 1)
                else:
                    now_x = checkpoint["population"]
            else:
                now_x = self.mutation.do(self.problem, self.population, inplace=True)
            
            if self.start_from_checkpoint:
                now_hpwl = checkpoint["fitness"]

                self.population = now_x
                self.population_hpwl = now_hpwl

                self.start_from_checkpoint = False
            else:
                result = self.problem.evaluate(now_x.get("X"), return_values_of=["F", "overlap_rate", "macro_pos"])
                now_hpwl, now_overlap_rate, now_macro_pos = result[0].item(), result[1].item(), result[2].item()

                if self.population_hpwl < now_hpwl:
                    # sa
                    exp_argument = (self.population_hpwl - now_hpwl) / self.T 
                    probability = np.exp(exp_argument)
                    if np.random.uniform(0, 1) < probability:
                        self.population = now_x
                        self.population_hpwl = now_hpwl
                else:
                    self.population = now_x
                    self.population_hpwl = now_hpwl 

            
                t_temp = time.time()
                t_eval = t_temp - t_start
                self.t_total += t_eval
                t_each_eval = t_temp - t_start
                avg_t_each_eval = self.t_total / (self.n_eval + self.args.n_population * 2)
                avg_t_eval_solution = self.placer.t_eval_solution_total / (self.n_eval + self.args.n_population * 2)

                self._record_results(
                    hpwl=np.array([now_hpwl]),
                    overlap_rate=np.array([now_overlap_rate]),
                    macro_pos_all=np.array([now_macro_pos]),
                    t_each_eval=t_each_eval,
                    avg_t_each_eval=avg_t_each_eval,
                    avg_t_eval_solution=avg_t_eval_solution,
                )

                # update temperature                
                if self.n_eval % self.update_freq == 0:
                    self.T = self.decay * self.T

            # save checkpoint
            # print(self.population.get('X'), self.population_hpwl)
            self._save_checkpoint(
                population=self.population,
                fitness=self.population_hpwl,
                temperature=self.T,
            )
    
    def _save_checkpoint(self, population, fitness, temperature):
        super()._save_checkpoint()

        with open(os.path.join(self.checkpoint_path, "sa.pkl"), "wb") as f:
            pickle.dump(
                {
                    "population" : population,
                    "fitness" : fitness,
                    "temperature" : temperature
                },
                file=f
            )
        
    
    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            super()._load_checkpoint()
            with open(os.path.join(self.args.checkpoint, "sa.pkl"), "rb") as f:
                checkpoint = pickle.load(f)
                self.start_from_checkpoint = True
        else:
                checkpoint = None
                self.start_from_checkpoint = False
        
        return checkpoint
            
    

        


            
