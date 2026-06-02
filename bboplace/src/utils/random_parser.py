import random
import numpy as np
import os
import torch as th

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    th.manual_seed(seed)
    th.cuda.manual_seed(seed)
    th.backends.cudnn.deterministic = True
    th.backends.cudnn.benchmark = False

def get_state():
    state_dict = {
        "random": random.getstate(),
        "np_random": np.random.get_state(),
        "th_random": th.get_rng_state()
    }
    if th.cuda.is_available():
        state_dict["th_cuda_random"] = th.cuda.get_rng_state()
    return state_dict

def set_state(state_dict):
    random.setstate(state_dict["random"])
    np.random.set_state(state_dict["np_random"])
    th.set_rng_state(state_dict["th_random"])
    if "th_cuda_random" in state_dict and th.cuda.is_available():
        th.cuda.set_rng_state(state_dict["th_cuda_random"])