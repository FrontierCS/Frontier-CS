import logging
import os
import sys
import json
import wandb
import pickle
import numpy as np

from utils.random_parser import get_state



class Logger:
    def __init__(self, args) -> None:
        self.args = args

        # write args
        config_dict = vars(args).copy()
        for key in list(config_dict.keys()):
            if not (isinstance(config_dict[key], str) or isinstance(config_dict[key], int) or isinstance(config_dict[key], float)):
                config_dict.pop(key)
        config_str = json.dumps(config_dict, indent=4)
        with open(os.path.join(args.result_path, "config.json"), 'w') as config_file:
                config_file.write(config_str)
                
        if args.use_wandb:
            if args.wandb_offline:
                os.environ["WANDB_MODE"] = "offline"
                wandb_logs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wandb_logs")
                os.makedirs(wandb_logs_path, exist_ok=True)
                os.environ["WANDB_DIR"] = wandb_logs_path

            if hasattr(args, "wandb_api"):
                wandb.login(key=args.wandb_api)
            self.logger = wandb.init(
                project=f"BBO4Placement",
                name=f"{args.name}_{args.benchmark}_{args.placer}_{args.algorithm}_{args.unique_token}",
                config=config_dict,
                group=f"{args.benchmark}",
                job_type=f"{args.job_type}"
            )
        else:
            self.logger = None
        
        self.log_info = {}
        self.log_checkpoint_info = {}

    def add(self, key, value):
        self.log_info[key] = value

        if key not in self.log_checkpoint_info:
            self.log_checkpoint_info[key] = [value]
        else:
            self.log_checkpoint_info[key].append(value)
    
    def step(self):
        # logging.info("logger saving log")
        if self.args.use_wandb:
            self.logger.log(self.log_info)
        self.log_info.clear()

    def _save_checkpoint(self, path:str):
        # log checkpoint
        random_state_dict = get_state()
        self.log_checkpoint_info.update(random_state_dict)
        with open(os.path.join(path, "log.pkl"), 'wb') as f:
            pickle.dump(self.log_checkpoint_info, f)

        






    
    