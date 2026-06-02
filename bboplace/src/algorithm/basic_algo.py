import os
import torch
import numpy as np
import logging
import pickle
from abc import abstractmethod
from utils.debug import *
from utils.constant import INF
from utils.random_parser import set_state

class BasicAlgo:
    def __init__(self, args, placer, logger) -> None:
        self.args = args
        self.placer = placer
        self.logger = logger

        self.n_eval = 0
        self.population = None
        self.best_hpwl = INF

        self.t_total = 0
        self.max_eval_time_second = args.max_eval_time * 60 * 60 

        self.checkpoint_path = os.path.join(args.result_path, "checkpoint")
        os.makedirs(self.checkpoint_path, exist_ok=True)
    
    
    @abstractmethod
    def run(self):
        pass

    def _record_results(self, hpwl, overlap_rate, macro_pos_all, t_each_eval=0, avg_t_each_eval=0, avg_t_eval_solution=0):
        if isinstance(hpwl, torch.Tensor):
            hpwl = hpwl.detach().cpu().numpy()
        hpwl = hpwl.flatten()
        best_idx = np.argmin(hpwl)
        pop_best_hpwl = hpwl[best_idx]
        pop_avg_hpwl = np.mean(hpwl)
        pop_std_hpwl = np.std(hpwl)


        for h, o_r, m_pos in zip(hpwl, overlap_rate, macro_pos_all):
            self.n_eval += 1
            if h < self.best_hpwl:
                self.best_hpwl = h
                logging.info(f"n_eval: {self.n_eval}\tbest_hpwl: {self.best_hpwl}\toverlap rate: {o_r}")
                self.placer.save_placement(
                    macro_pos=m_pos,
                    n_eval=self.n_eval,
                    hpwl=h
                )
                self.placer.plot(
                    macro_pos=m_pos,
                    n_eval=self.n_eval,
                    hpwl=h
                )

            self.logger.add("HPWL/his_best", self.best_hpwl)
            self.logger.add("HPWL/pop_best", pop_best_hpwl)
            self.logger.add("HPWL/pop_avg", pop_avg_hpwl)
            self.logger.add("HPWL/pop_std", pop_std_hpwl)
            self.logger.add("overlap_rate", o_r)
            self.logger.add("Time/each_eval", t_each_eval)
            self.logger.add("Time/avg_each_eval", avg_t_each_eval)
            self.logger.add("Time/avg_algo_optimization", avg_t_each_eval - avg_t_eval_solution)
            self.logger.add("Time/avg_eval_solution", avg_t_eval_solution)

            self.logger.step()

            self.placer.save_metrics(
                n_eval=self.n_eval,
                his_best_hpwl=self.best_hpwl,
                pop_best_hpwl=pop_best_hpwl,
                pop_avg_hpwl=pop_avg_hpwl,
                pop_std_hpwl=pop_std_hpwl,
                overlap_rate=o_r,
                t_each_eval=t_each_eval,
                avg_t_each_eval=avg_t_each_eval,
                avg_t_eval_solution=avg_t_eval_solution
            )
        
        
        if self.args.eval_gp_hpwl:
            self.placer.gp_evaluator.empty_saving_data()


    def _save_checkpoint(self):
        logging.info("saving checkpoint")

        # logger checkpoint
        self.logger._save_checkpoint(path=self.checkpoint_path)

        # placement and corresponding figure checkpoint
        self.placer._save_checkpoint(checkpoint_path=self.checkpoint_path)

        if self.t_total >= self.max_eval_time_second:
            logging.info(f"Reaching maximun running time ({self.t_total:.2f} >= {self.max_eval_time_second}), the program will exit")
            exit(0)

        
    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            logging.info(f"Loading checkpoint from {self.args.checkpoint}")
            log_file = os.path.join(self.args.checkpoint, "log.pkl")
            with open(log_file, 'rb') as log_f:
                log_data = pickle.load(log_f)
            
            self.n_eval = len(log_data["HPWL/his_best"])
            assert self.n_eval == len(log_data["HPWL/pop_best"]) 
            assert self.n_eval == len(log_data["HPWL/pop_avg"]) 
            assert self.n_eval == len(log_data["HPWL/pop_std"]) 
            assert self.n_eval == len(log_data["overlap_rate"])
            assert self.n_eval == len(log_data["Time/each_eval"]) 
            assert self.n_eval == len(log_data["Time/avg_each_eval"]) 
            assert self.n_eval == len(log_data["Time/avg_algo_optimization"]) 
            assert self.n_eval == len(log_data["Time/avg_eval_solution"]) 
            
            set_state(log_data)

            for i_eval in range(0, self.n_eval):
                self.logger.add("HPWL/his_best", log_data["HPWL/his_best"][i_eval])
                self.logger.add("HPWL/pop_best", log_data["HPWL/pop_best"][i_eval])
                self.logger.add("HPWL/pop_avg", log_data["HPWL/pop_avg"][i_eval])
                self.logger.add("HPWL/pop_std", log_data["HPWL/pop_std"][i_eval])
                self.logger.add("overlap_rate", log_data["overlap_rate"][i_eval])
                self.logger.add("Time/each_eval", log_data["Time/each_eval"][i_eval])
                self.logger.add("Time/avg_each_eval", log_data["Time/avg_each_eval"][i_eval])
                self.logger.add("Time/avg_algo_optimization", log_data["Time/avg_algo_optimization"][i_eval])
                self.logger.add("Time/avg_eval_solution", log_data["Time/avg_eval_solution"][i_eval])
                self.logger.step()

                self.placer.save_metrics(
                    n_eval=i_eval+1,
                    his_best_hpwl=log_data["HPWL/his_best"][i_eval],
                    pop_best_hpwl=log_data["HPWL/pop_best"][i_eval],
                    pop_avg_hpwl=log_data["HPWL/pop_avg"][i_eval],
                    pop_std_hpwl=log_data["HPWL/pop_std"][i_eval],
                    overlap_rate=log_data["overlap_rate"][i_eval],
                    t_each_eval=log_data["Time/each_eval"][i_eval],
                    avg_t_each_eval=log_data["Time/avg_each_eval"][i_eval],
                    avg_t_eval_solution=log_data["Time/avg_eval_solution"][i_eval],
                )
            self.best_hpwl = log_data["HPWL/his_best"][self.n_eval-1]
            self.t_total   = sum(log_data["Time/each_eval"])

            self.placer.t_eval_solution_total = log_data["Time/avg_eval_solution"][-1] * self.n_eval
            self.placer._load_checkpoint(checkpoint_path=self.args.checkpoint)

