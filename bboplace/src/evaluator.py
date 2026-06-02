import os 
from config.benchmark import (
    ROOT_DIR, BENCHMARK_DIR, benchmark_dict, 
    benchmark_type_dict, benchmark_n_macro_dict
)
THIRDPARTY_DIR = os.path.join(ROOT_DIR, "thirdparty")
DREAMPLACE_DIR = os.path.join(THIRDPARTY_DIR, "dreamplace")
SOURCE_DIR = os.path.join(ROOT_DIR, "src")
import sys
sys.path.extend(
    [
        ROOT_DIR, 
        BENCHMARK_DIR, 
        THIRDPARTY_DIR, 
        DREAMPLACE_DIR, 
        SOURCE_DIR
    ]
)
os.environ["PYTHONPATH"] = ":".join(sys.path)

# from placedb import PlaceDB
from src.placedb import PlaceDB
from src.placer import REGISTRY as PLACER_REGISTRY
from src.utils.debug import *
from argparse import Namespace
import numpy as np 
import datetime 

import logging
import yaml
import ray
from src.placer.hpo_placer import params_space




class Evaluator:
    def __init__(self, args: Namespace):
        assert "placer" in args.__dict__.keys() 
        assert "benchmark" in args.__dict__.keys()   
        assert "eval_gp_hpwl" in args.__dict__.keys() 
        file_config_dict = {} 
        
        config_path = os.path.join(
            ROOT_DIR, "config"
        )
        assert os.path.exists(config_path)
        
        with open(os.path.join(config_path, "default.yaml"), "r") as f:
            file_config_dict.update(
                yaml.load(f, Loader=yaml.FullLoader)
            )

        args.placer = args.placer.lower()
        
        with open(os.path.join(config_path, "placer", f"{args.placer}.yaml"),
                  "r") as f:
            try:
                file_config_dict.update(
                    yaml.load(f, Loader=yaml.FullLoader)
                )
            except:
                pass 
          
        file_config_dict["ROOT_DIR"] = ROOT_DIR
        file_config_dict["THIRDPARTY_DIR"] = THIRDPARTY_DIR
        file_config_dict["SOURCE_DIR"] = SOURCE_DIR

        # Set benchmark kwargs
        is_benchmark_registered = False
        for benchmark_base in benchmark_dict:
            if args.benchmark in benchmark_dict[benchmark_base]:
                is_benchmark_registered = True
                break
        if not is_benchmark_registered:
            assert0("benchmark was not registered in config/benchmark.py")

        # set n_macro
        file_config_dict["n_macro"] = benchmark_n_macro_dict[benchmark_base]

        benchmark_path = os.path.join(BENCHMARK_DIR, benchmark_base, args.benchmark)
        benchmark_type = benchmark_type_dict[benchmark_base]
        
        file_config_dict["benchmark_base"] = benchmark_base
        file_config_dict["benchmark_path"] = benchmark_path
        file_config_dict["benchmark_type"] = benchmark_type

        # Set other params 
        unique_token = "seed_{}_{}".format(args.seed, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        result_path = os.path.join(ROOT_DIR, 
                                    f"results/{args.benchmark}/{args.placer}/{unique_token}")
        os.makedirs(result_path, exist_ok=True)
        file_config_dict["unique_token"] = unique_token
        file_config_dict["result_path"] = result_path

        new_params = {k: v for k, v in file_config_dict.items() if k not in args.__dict__}
        args.__dict__.update(new_params)
        
        self.args = args 
        self.placedb = PlaceDB(args=args)
        self.placer = PLACER_REGISTRY[args.placer](args=args, placedb=self.placedb)

        ray.init(num_cpus=64,
            num_gpus=1,
            include_dashboard=False,
            logging_level=logging.CRITICAL,
            _temp_dir=os.path.expanduser('~/tmp'),
            ignore_reinit_error=True,
            log_to_driver=False)

    @property
    def n_dim(self):
        if self.args.placer in ["mgo", "sp"]:
            node_cnt = self.placer.placedb.node_cnt 
            return node_cnt * 2
        elif self.args.placer == "hpo":
            return len(params_space.keys())
        else:
            raise ValueError(f"Not supported placer {self.args.placer}")

    @property
    def xl(self):
        if self.args.placer in ["mgo", "sp"]:
            node_cnt = self.placer.placedb.node_cnt 
            return np.zeros(node_cnt * 2)
        elif self.args.placer == "hpo":
            extract = lambda ent_i: \
                [entry[ent_i] for entry in params_space.values()]
            return np.array(extract(0))
        else:
            raise ValueError(f"Not supported placer {self.args.placer}")
        
    @property
    def xu(self):
        if self.args.placer == "mgo":
            node_cnt = self.placer.placedb.node_cnt 
            n_grid_x = self.args.n_grid_x
            n_grid_y = self.args.n_grid_y 
            return np.array(
                ([n_grid_x] * node_cnt) + ([n_grid_y] * node_cnt)
            )
        elif self.args.placer == "sp":
            node_cnt = self.placer.placedb.node_cnt 
            return np.array([node_cnt] * node_cnt * 2)
        elif self.args.placer == "hpo":
            extract = lambda ent_i: \
                [entry[ent_i] for entry in params_space.values()]
            return np.array(extract(1))
        else:
            raise ValueError(f"Not supported placer {self.args.placer}")        

    def evaluate(self, x):
        if isinstance(x, list):
            x = np.array(x)
        if x.shape == 1:
            x = x.reshape(1, -1)

        hpwl, overlap_rate, macro_pos = self.placer.evaluate(x)

        return np.array(hpwl)



        
