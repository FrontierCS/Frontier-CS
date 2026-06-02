from abc import abstractmethod
from src.utils.debug import *
from src.utils.compute_res import comp_res, comp_overlap
from src.utils.read_benchmark.read_aux import write_pl
from src.utils.read_benchmark.read_def import write_def
from src.utils.constant import get_n_power

from typing import overload

import os
import csv
import ray
import time
import logging
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches

@ray.remote(num_cpus=1, num_gpus=0.1)
def evaluate_placer(placer, x0):
    return placer._evaluate(x0)

class BasicPlacer:
    def __init__(self, args, placedb) -> None:
        self.args = args
        self.placedb = placedb

        self.canvas_width  = placedb.canvas_width
        self.canvas_height = placedb.canvas_height
        
        self.fig_save_path       = os.path.join(args.result_path, "figures")
        self.placement_save_path = os.path.join(args.result_path, "placements")
        os.makedirs(self.fig_save_path, exist_ok=True)
        os.makedirs(self.placement_save_path, exist_ok=True)

        self.metrics_file = os.path.join(args.result_path, "metrics.csv")
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.writer(f)
            header = [
                "n_eval", 
                "his_best_hpwl", 
                "pop_best_hpwl", 
                "pop_avg_hpwl", 
                "pop_std_hpwl", 
                "overlap_rate", 
                "t_each_eval", 
                "avg_t_each_eval",
                "avg_t_algo_optimization",
                "avg_t_eval_solution"
            ]
            writer.writerow(header)
        
        self.placement_saving_lst = []
        self.figure_saving_lst = []
        self.n_max_saving_placement = args.n_max_saving_placement

        if self.args.eval_gp_hpwl:
            from gp_evaluator import GPEvaluator
            self.gp_evaluator = GPEvaluator(args=args,
                                            placedb=placedb)
            
        self.t_eval_solution_total = 0

    def _evaluate(self, x):
        # t = time.time()
        macro_pos = self._genotype2phenotype(x)
        if self.args.eval_gp_hpwl:
            hpwl = self.gp_evaluator.evaluate(macro_pos=macro_pos)
        else:
            hpwl = comp_res(macro_pos=macro_pos, placedb=self.placedb)
        overlap_rate = comp_overlap(macro_pos=macro_pos, placedb=self.placedb)
        # t_eval_solution = time.time() - t
        return hpwl, overlap_rate, macro_pos
    
    
    def evaluate(self, x):
        t = time.time()
        if self.args.n_cpu_max > 1 and \
            not self.args.eval_gp_hpwl and \
            self.args.placer != "hpo":
            futures = [evaluate_placer.remote(self, x0) for x0 in x]
            results = ray.get(futures)
        else:
            results = [self._evaluate(x0) for x0 in x]
        t_eval_solution = time.time() - t
        
        hpwl_all = []
        overlap_rate_all = []
        macro_pos_all = []
        for hpwl, overlap_rate, macro_pos in results:
            hpwl_all.append(hpwl)
            overlap_rate_all.append(overlap_rate)
            macro_pos_all.append(macro_pos)
        self.t_eval_solution_total += t_eval_solution
        return hpwl_all, overlap_rate_all, macro_pos_all

    def save_placement(self, macro_pos, n_eval, hpwl):
        logging.info("Placer saving placement")
        scale_hpwl, n_power = get_n_power(hpwl)

        delete_file_name = None
        if len(self.placement_saving_lst) == self.n_max_saving_placement:
            delete_file_name = self.placement_saving_lst.pop(0)
        
        suffix_map = {
            "aux" : "pl",
            "def" : "def"
        }
        suffix = suffix_map[self.args.benchmark_type]
        file_name = os.path.join(self.placement_save_path, 
                                f'{n_eval}_{scale_hpwl:.2f}e{n_power}.{suffix}')
        if self.args.eval_gp_hpwl:
            self.gp_evaluator.save_placement(hpwl=hpwl, placement_name=file_name)
        else:
            type_map = {
                "aux" : write_pl,
                "def" : write_def
            }
            type_map[self.args.benchmark_type](file_name, macro_pos, self.placedb)
        
        if delete_file_name is not None:
            os.remove(delete_file_name)
        self.placement_saving_lst.append(file_name)
        assert len(self.placement_saving_lst) <= self.n_max_saving_placement

    def plot(self, macro_pos:dict, n_eval:int, hpwl:float):
        logging.info("Placer ploting figure")
        scale_hpwl, n_power = get_n_power(hpwl)

        delete_file_name = None
        if len(self.figure_saving_lst) == self.n_max_saving_placement:
            delete_file_name = self.figure_saving_lst.pop(0)

        file_name = os.path.join(self.fig_save_path, f"{n_eval}_{scale_hpwl:.2f}e{n_power}.png")
        if self.args.eval_gp_hpwl:
            self.gp_evaluator.plot(hpwl=hpwl, figure_name=file_name)
        else:
            self._plot_macro(macro_pos, file_name)

        if delete_file_name is not None:
            os.remove(delete_file_name)
        self.figure_saving_lst.append(file_name)
        assert len(self.figure_saving_lst) <= self.n_max_saving_placement

    def _plot_macro(self, macro_pos, file_name):
        fig = plt.figure()
        ax = fig.add_subplot(111, aspect="auto")
        ax.axes.xaxis.set_visible(False)
        ax.axes.yaxis.set_visible(False)
        for macro in macro_pos:
            pos_x, pos_y = macro_pos[macro]
            size_x, size_y = self.placedb.node_info[macro]["size_x"], self.placedb.node_info[macro]["size_y"]

            pos_x = pos_x / self.placedb.canvas_ux
            pos_y = pos_y / self.placedb.canvas_uy
            size_x = size_x / self.placedb.canvas_ux
            size_y = size_y / self.placedb.canvas_uy
            ax.add_patch(
                patches.Rectangle(
                    (pos_x, pos_y),
                    size_x, size_y,
                    linewidth=1, edgecolor='k'
                )
            )

        fig.savefig(file_name, dpi=90, bbox_inches='tight')
        plt.close()
        
    def save_metrics(
            self, 
            n_eval, 
            his_best_hpwl, 
            pop_best_hpwl, 
            pop_avg_hpwl, 
            pop_std_hpwl,
            overlap_rate,
            t_each_eval=0,
            avg_t_each_eval=0,
            avg_t_eval_solution=0,
            ):
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.writer(f)
            content = [
                n_eval, 
                his_best_hpwl, 
                pop_best_hpwl, 
                pop_avg_hpwl, 
                pop_std_hpwl, 
                overlap_rate, 
                t_each_eval, 
                avg_t_each_eval,
                avg_t_each_eval - avg_t_eval_solution,
                avg_t_eval_solution
            ]
            writer.writerow(content)

    def _save_checkpoint(self, checkpoint_path):
        def save_and_delete(set_new, set_old, is_placement=True):
            if is_placement:
                suffix = "placements"
            else:
                suffix = "figures"
            for file_name in set_old - set_new:
                os.system(f"rm {os.path.join(checkpoint_path, suffix, file_name)}")
            
            for file_name in set_new - set_old:
                if is_placement:
                    os.system(f"cp {os.path.join(self.placement_save_path, file_name)} "+\
                              f"{os.path.join(checkpoint_path, suffix, file_name)}")
                else:
                    os.system(f"cp {os.path.join(self.fig_save_path, file_name)} "+\
                              f"{os.path.join(checkpoint_path, suffix, file_name)}")

        os.makedirs(os.path.join(checkpoint_path, "placements"), exist_ok=True)
        os.makedirs(os.path.join(checkpoint_path, "figures"), exist_ok=True)
        
        placement_set_old = set(os.listdir(os.path.join(checkpoint_path, "placements")))
        placement_set_new = set([os.path.basename(file_name) for file_name in self.placement_saving_lst])

        figure_set_old = set(os.listdir(os.path.join(checkpoint_path, "figures")))
        figure_set_new = set([os.path.basename(file_name) for file_name in self.figure_saving_lst])

        save_and_delete(placement_set_new, placement_set_old, is_placement=True)
        save_and_delete(figure_set_new, figure_set_old, is_placement=False)

    def _load_checkpoint(self, checkpoint_path):
        for file_name in os.listdir(os.path.join(checkpoint_path, "placements")):
            self.placement_saving_lst.append(os.path.join(self.placement_save_path, file_name))
            os.system(f"cp {os.path.join(checkpoint_path, 'placements', file_name)} "+\
                      f"{os.path.join(self.placement_save_path, file_name)}")

        for file_name in os.listdir(os.path.join(checkpoint_path, "figures")):
            self.figure_saving_lst.append(os.path.join(self.fig_save_path, file_name))
            os.system(f"cp {os.path.join(checkpoint_path, 'figures', file_name)} "+\
                      f"{os.path.join(self.fig_save_path, file_name)}")

        self.placement_saving_lst = sorted(self.placement_saving_lst, key=lambda x:int(os.path.basename(x).split('_')[0]))
        self.figure_saving_lst = sorted(self.figure_saving_lst, key=lambda x:int(os.path.basename(x).split('_')[0]))
        

    @abstractmethod
    def _genotype2phenotype(self, x):
        pass

    def __deepcopy__(self, memo=None):
        return self



