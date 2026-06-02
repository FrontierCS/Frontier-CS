import csv
import os
import time
import shutil
import numpy as np
import pandas as pd

from config.benchmark import benchmark_dict, benchmark_power_config, benchmark_type_dict
from utils.debug import *

def res2sheet(args, sheet_path, res_path):
    placer_name = args.placer.lower()
    algo_name = args.algorithm.upper()
    if args.eval_gp_hpwl:
        placer_name += "(GP eval)"
        power_config = benchmark_power_config["gp"]
    else:
        power_config = benchmark_power_config["mp"]

    # get results
    hpwl_lst = []
    not_complete_lst = []
    n_seed = 0
    for seed in os.listdir(res_path):
        seed_file = os.path.join(res_path, seed, "metrics.csv") 
        df = pd.read_csv(seed_file)
        l = len(list(df["n_eval"]))
        if l > 0:
            hpwl_lst.append(list(df["his_best_hpwl"])[l-1])
            n_seed += 1
    if len(hpwl_lst) == 0:
        assert0(f"No result found in {res_path}")
    
    hpwl_mean = np.mean(hpwl_lst) / power_config[args.benchmark_base]
    hpwl_std  = np.std(hpwl_lst) / power_config[args.benchmark_base]
    hpwl_content = f"{hpwl_mean:.2f}$\\pm${hpwl_std:.2f} (n_seed={n_seed})"
    
    # write to sheet
    sheet_file = os.path.join(sheet_path, f"{args.benchmark_base}.csv")
    if not os.path.exists(sheet_file):
        with open(sheet_file, 'a') as f:
            writer = csv.writer(f)
            content = ["placer", "algorithm"] + benchmark_dict[args.benchmark_base]
            writer.writerow(content)
    
    assert args.benchmark in benchmark_dict[args.benchmark_base]
    benchmark_idx = benchmark_dict[args.benchmark_base].index(args.benchmark)
    with open(sheet_file, 'r') as f:
        reader = csv.reader(f)

        # temp file
        row_exist = False
        temp_sheet_file = os.path.join(sheet_path, f"{args.benchmark_base}_temp.csv")
        with open(temp_sheet_file, 'w') as temp_f:
            writer = csv.writer(temp_f)
            content = []
            for row in reader:
                if row[0] == placer_name and row[1] == algo_name:
                    row_exist = True
                    highlight("row exist")
                    row[2 + benchmark_idx] = hpwl_content
                content.append(row)
            
            if not row_exist:
                hpwl_lst = ["0.00$\\pm$0.00 (n_seed=0)" for _ in range(len(benchmark_dict[args.benchmark_base]))]
                hpwl_lst[benchmark_idx] = hpwl_content
                row = [placer_name, algo_name] + hpwl_lst
                content.append(row)
            
            writer.writerows(content)
    
    shutil.move(temp_sheet_file, sheet_file)
        