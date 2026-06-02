import os 
import sys
import argparse
import datetime
import re
import csv
import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, distributions

import logging
logging.root.name = 'BBO4Placement'
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)-7s] %(name)s - %(message)s',
                    stream=sys.stdout)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
sys.path.append(ROOT_DIR)
os.environ["PYTHONPATH"] = ":".join(sys.path)

from config.benchmark import benchmark_dict
from debug import *

parser = argparse.ArgumentParser(description='notability analysis parser')
parser.add_argument("--sheet_path", type=str, default=os.path.join(ROOT_DIR, "sheets", "ispd2005.csv"), help="path of the result sheet")
parser.add_argument("--benchmark", type=str, default="adaptec1", help="the benchmark used for evaluating the algorithm")
parser.add_argument("--eval_gp_hpwl", action='store_true', help='analysis on gp hpwl')
parser.add_argument("--default_n_seed", type=int, default=5, help="default amount of seed")

args = parser.parse_args()

mean_std_format = r"(\d+\.\d+)\$\\pm\$(\d+(\.\d+)?)"
n_seed_format   = r"n_seed=(\d+)"

class NotabilityAnalysis:
    def __init__(self, args) -> None:
        self.args = args
        self.sheet_path = args.sheet_path
        self.benchmark = args.benchmark
        assert os.path.exists(self.sheet_path), "Sheet file doesn't exist"

    def calculate_p_values(self, method_value_map):
        best_method = min(method_value_map.keys(), key=lambda x: method_value_map[x]["mean"])
        
        p_value_map = {}
        for method, value_dict in method_value_map.items():
            if method == best_method:
                p_value_map[method] = float("nan")
            else:
                df, denom = self._equal_var_ttest_denom(
                    v1=value_dict["var"],
                    n1=value_dict["n_seed"],
                    v2=method_value_map[best_method]["var"],
                    n2=method_value_map[best_method]["n_seed"]
                )
                t, prob = self._ttest_ind_from_stats(
                    m1=value_dict["mean"], 
                    m2=method_value_map[best_method]["mean"], 
                    denom=denom, 
                    df=df
                )
                p_value_map[method] = prob
        
        return p_value_map
    
    def save_result(self, method_value_map, p_value_map):
        # write to sheet
        saved_file_name = None
        benchmark_base = None
        for benchmark_base in benchmark_dict:
            if self.benchmark in benchmark_dict[benchmark_base]:
                saved_file_name = benchmark_base + f"_{'gp' if self.args.eval_gp_hpwl else 'mp'}_ttest.csv"
                break
        
        if saved_file_name is None:
            assert0("benchmark was not registered in config/benchmark.py")

        saved_sheet_dir = os.path.dirname(self.sheet_path)
        saved_sheet_file = os.path.join(saved_sheet_dir, saved_file_name)

        if benchmark_base == "ispd2005":
            header = ["placer", "algorithm"] + [f"adaptec{i}" for i in range(1,5)] + ["bigblue1", "bigblue3"]
        else:
            header = ["placer", "algorithm"] + benchmark_dict[benchmark_base]

        if os.path.exists(saved_sheet_file):
            result_df = pd.read_csv(saved_sheet_file, sep=',')
        else:
            result_df = pd.DataFrame(columns=header)

        for method in method_value_map.keys():
            placer = method_value_map[method]["placer"]
            algo   = method_value_map[method]["algo"]
            value  = method_value_map[method]["value"]
            mean_std_str = method_value_map[method]["mean_std_str"]
            p      = p_value_map[method]


            if not result_df[(result_df['placer'] == placer) &\
                             (result_df['algorithm'] == algo)].empty:
                result_df.loc[(result_df['placer'] == placer) &\
                              (result_df['algorithm'] == algo),
                              self.benchmark] = f"{mean_std_str} " + ('-' if p < 0.05 else '$\\approx$')
            else:
                row = dict.fromkeys(header, " ")
                row["placer"] = placer
                row["algorithm"] = algo
                row[self.benchmark] = f"{method_value_map[method]['mean_std_str']} " + ('-' if p < 0.05 else '$\\approx$')
                result_df.loc[len(result_df)] = row
        
        result_df = self._highlight_best_two(result_df=result_df, ascending=True)
        result_df.to_csv(saved_sheet_file, sep=',', index=False)
        logging.info(f"Successfully save result to {saved_sheet_file}")
            

    def process_sheet_file(self):
        sheet_content = pd.read_csv(self.sheet_path)

        method_value_map = {}
        for index, row in sheet_content.iterrows():
            placer = row["placer"]
            algo   = row["algorithm"]
            value  = row[self.args.benchmark]

            if (self.args.eval_gp_hpwl and "GP" in placer) or\
               (not self.args.eval_gp_hpwl and not "GP" in placer):
                method = f"{placer}/{algo}"
                mean_std = re.search(pattern=mean_std_format, string=value)
                n_seed   = re.search(pattern=n_seed_format,   string=value)

                if mean_std is None:
                    continue
                
                mean_std_str = mean_std.group(0)
                mean = eval(mean_std.group(1))
                var  = (eval(mean_std.group(2))**2)
                n_seed = self.args.default_n_seed if n_seed is None else eval(n_seed.group(1))

                if mean == 0 and var == 0:
                    continue
                method_value_map[method] = {
                    "mean" : mean,
                    "var" : var,
                    "n_seed" : n_seed,
                    "placer" : placer,
                    "algo" : algo,
                    "value" : value,
                    "mean_std_str" : mean_std_str,
                }
        
        return method_value_map

    def _equal_var_ttest_denom(self, v1, n1, v2, n2):
        df = n1 + n2 - 2.0
        svar = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
        denom = np.sqrt(svar * (1.0 / n1 + 1.0 / n2))
        return df, denom
    
    def _unequal_var_ttest_denom(self, v1, n1, v2, n2):
        vn1 = v1 / n1
        vn2 = v2 / n2
        with np.errstate(divide='ignore', invalid='ignore'):
            df = (vn1 + vn2)**2 / (vn1**2 / (n1 - 1) + vn2**2 / (n2 - 1))

        df = np.where(np.isnan(df), 1, df)
        denom = np.sqrt(vn1 + vn2)
        return df, denom
    
    def _ttest_ind_from_stats(self, m1, m2, denom, df):
        d = m1 - m2
        with np.errstate(divide='ignore', invalid='ignore'):
            t = np.divide(d, denom)[()]
        prob = self._get_pvalue(t, distributions.t(df))
        return (t, prob)

    def _get_pvalue(self, statistic, distribution):
        pvalue = 2 * distribution.sf(np.abs(statistic)) 
        return pvalue
    
    def _highlight_best_two(self, result_df, ascending=True):
        try:
            means = result_df[self.benchmark].apply(lambda x: float(x.split('$\pm$')[0].strip()))
        except:
            import pdb; pdb.set_trace()

        sorted_means = means.sort_values(ascending=ascending)
        best_two = sorted_means.head(2).index

        new_result_df = result_df.copy()
        if len(best_two) > 0:
            original_value = new_result_df.loc[best_two[0], self.benchmark]
            new_result_df.loc[best_two[0], self.benchmark] = f"\\textbf{{{original_value}}}"
        if len(best_two) > 1:
            original_value = new_result_df.loc[best_two[1], self.benchmark]
            new_result_df.loc[best_two[1], self.benchmark] = f"\\underline{{{original_value}}}"
        
        return new_result_df
        
if __name__ == "__main__":
    notability_analysis = NotabilityAnalysis(args=args)
    method_value_map = notability_analysis.process_sheet_file()
    p_value_map = notability_analysis.calculate_p_values(
        method_value_map=method_value_map
    )
    notability_analysis.save_result(
        method_value_map=method_value_map,
        p_value_map=p_value_map
    )
    
