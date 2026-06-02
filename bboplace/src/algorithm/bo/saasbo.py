import numpy as np 
import torch 
import ray
import logging
import pickle 
import os
import sys
from torch import Tensor
import gpytorch
import time 
import math
import psutil
from collections import deque
from copy import deepcopy

# from botorch import fit_fully_bayesian_model_nuts
from botorch.fit import fit_fully_bayesian_model_nuts
# from botorch.acquisition import ExpectedImprovement
from botorch.acquisition.monte_carlo import qExpectedImprovement 
    
from botorch.models.fully_bayesian import SaasFullyBayesianSingleTaskGP

from gpytorch.kernels import Kernel
from botorch.optim import optimize_acqf
from botorch.utils.transforms import normalize, unnormalize
from botorch.models.transforms.outcome import Standardize

from .kernel import TransformedCategorical, OrderKernel, CombinedOrderKernel
from utils.debug import * 
from utils.constant import INF
from utils.data_utils import FeatureCache 
from utils.random_parser import set_state
from problem.acqf_problem import MaskGuidedOptimizationAcquisitionFuncProblem, SequencePairAcquisitionFuncProblem
from operators import REGISTRY as OPS_REGISTRY
from problem.pymoo_problem import (
    MaskGuidedOptimizationPlacementProblem, 
    SequencePairPlacementProblem,
    HyperparameterPlacementProblem
)
from pymoo.operators.sampling.rnd import FloatRandomSampling, PermutationRandomSampling
from pymoo.operators.mutation.pm import PM
from pymoo.operators.mutation.inversion import InversionMutation
from pymoo.operators.crossover.ox import OrderCrossover
from pymoo.operators.crossover.sbx import SBX
from pymoo.core.repair import Repair
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.optimize import minimize
from placer.hpo_placer import params_space
from ..basic_algo import BasicAlgo


class _SPRandomSampling(PermutationRandomSampling):
    def __init__(self, args, placer) -> None:
        super(_SPRandomSampling, self).__init__()
        self.args = args
        self.placer = placer
    
    def _do(self, problem, n_samples, **kwargs):
        sub_n_var = problem.n_var // 2
        sub_xl = problem.xl[:sub_n_var]
        sub_xu = problem.xu[:sub_n_var]
        sub_problem = deepcopy(problem)
        sub_problem.n_var = sub_n_var
        sub_problem.xl = sub_xl
        sub_problem.xu = sub_xu
        X1 = PermutationRandomSampling._do(self, problem=sub_problem, 
                                               n_samples=n_samples)
        X2 = PermutationRandomSampling._do(self, problem=sub_problem, 
                                               n_samples=n_samples)
        X = np.concatenate([X1, X2], axis=1)
        return X

tkwargs = {
    "dtype": torch.double,
    "device": torch.device("cuda" if torch.cuda.is_available() else "cpu"),
}


class IntegerRandomSampling(FloatRandomSampling):

    def _do(self, problem, n_samples, **kwargs):
        X = super()._do(problem, n_samples, **kwargs)
        return np.around(X).astype(int)

from placer.basic_placer import evaluate_placer

class SAASBO(BasicAlgo):
    def __init__(self, args, placer, logger):
        super(SAASBO, self).__init__(args=args, placer=placer, logger=logger)
        
        self.n_var = placer.placedb.node_cnt
        
        self.placer = placer
        self.placer_type = args.placer 
        self.n_init = self.args.n_init 
        self.batch_size = self.args.batch_size
        
        self.acqf_type = self.args.acqf_type 
        self.kernel_type = None

        self.warmup_steps = self.args.warmup_steps
        self.num_samples = self.args.num_samples
        self.thinning = self.args.thinning
        
        if args.placer == "mgo":
            self.problem = MaskGuidedOptimizationPlacementProblem(
                n_grid_x=args.n_grid_x,
                n_grid_y=args.n_grid_y,
                placer=placer
            )
            self.kernel_type = "default"
            self.acqf_type = "EI"
            
            self.dim = self.n_var * 2
            bounds_ = np.zeros((2, self.dim))
            xu = np.array(
                ([args.n_grid_x - 1] * self.n_var) + \
                    ([args.n_grid_y - 1] * self.n_var)
            )
            bounds_[1] = xu
            self.bounds = torch.from_numpy(bounds_).to(**tkwargs)
            
        elif args.placer == "sp":
            self.problem = SequencePairPlacementProblem(
                placer=placer
            )
            self.kernel_type = "comb_order"
            self.acqf_type = 'LCB_lower_bound'
            
        elif args.placer == "hpo":
            self.problem = HyperparameterPlacementProblem(
                params_space=params_space,
                placer=placer
            )
            self.kernel_type = "default"
            self.acqf_type = "EI"
            
            self.params_space = params_space
            self.dim = len(self.params_space.keys())
            extract = lambda ent_i: \
                [entry[ent_i] for entry in self.params_space.values()]
            bounds_ = np.ones((2, self.dim))
            bounds_[0] = np.array(extract(0))
            bounds_[1] = np.array(extract(1))
            self.bounds = torch.from_numpy(bounds_).to(**tkwargs)
            
        else:
            raise NotImplementedError
        
        self.args.__dict__.update(
            {"logger": logger, "record_func": self._record_results}
        )
        
    
    def _init_model(self, train_X: Tensor, train_Y: Tensor, state_dict=None):
        assert not torch.isnan(train_X).any() and not torch.isinf(train_X).any()
        assert not torch.isnan(train_Y).any() and not torch.isinf(train_Y).any()
        
        model = SaasFullyBayesianSingleTaskGP(
            train_X, train_Y,
            outcome_transform=Standardize(m=1)
        ).to(**tkwargs)
        if state_dict is not None:
            model.load_state_dict(state_dict)
        fit_fully_bayesian_model_nuts(
            model,
            warmup_steps=self.warmup_steps,
            num_samples=self.num_samples,
            thinning=self.thinning,
            disable_progbar=True,
        )
        return model
    
    def _init_samples(self, n_samples):  
        x_np = OPS_REGISTRY["sampling"][self.placer_type]["random"](self.args, self.placer) \
               .do(self.problem, n_samples).get("X")
        x = torch.from_numpy(x_np).to(**tkwargs)

        hpwl, overlap_rate, macro_pos_all = self._get_observations(x, return_macro_pos=True)
        self._record_results(hpwl, overlap_rate, macro_pos_all)
        
        if isinstance(hpwl, (np.ndarray, list)):
            hpwl = torch.Tensor(hpwl).to(**tkwargs)
        
        return x, hpwl.reshape(-1, 1)
    
    def _get_kernel(self, kernel_type):
        if kernel_type.lower() == "tc":
            kernel = TransformedCategorical()
        elif kernel_type.lower() == "comb_order":
            kernel = CombinedOrderKernel(n=self.placer.placedb.node_cnt)
        elif kernel_type.lower() == "default":
            kernel = None 
        else:
            raise NotImplementedError
        return kernel 
            
            
    def _get_acqf(self, acqf_type, model, train_X: Tensor, train_Y: Tensor):
        if acqf_type == 'EI':
            AF = qExpectedImprovement(
                model, best_f=train_Y.min().item(), maximize=False).to(**tkwargs)
            
        elif acqf_type == 'LCB_lower_bound':
            def LCB_lower_bound(X: Tensor):
                with torch.no_grad():
                    X = X.to(**tkwargs)
                    posterior = model.posterior(X)
                    mean = posterior.mean
                    var = posterior.variance
                    return mean - 0.2*(torch.sqrt(var))
            AF = LCB_lower_bound
            
        else:
            raise NotImplementedError
        return AF
            

    def _get_observations(self, x, return_macro_pos=True):
        is_torch_tensor = isinstance(x, torch.Tensor)
        
        if is_torch_tensor:
            if self.placer_type != "hpo":
                x = np.round(x.detach().cpu().numpy()).astype(np.int32)
            else:
                x = x.detach().cpu().numpy()
        
        y, overlap_rate, macro_pos_all = self.placer.evaluate(x)
        return np.array(y), np.array(overlap_rate), (macro_pos_all if return_macro_pos else None)
        
    def _optimize_acqf_and_get_observations(self, acqf, num_samples=1):
        if self.placer_type == "sp":
            acqf_problem = SequencePairAcquisitionFuncProblem(
                node_cnt=self.placer.placedb.node_cnt, acqf=acqf
            )
            algo = GA(
                pop_size=100,
                sampling=_SPRandomSampling(args=self.args, placer=self.placer),
                mutation=OPS_REGISTRY["mutation"][self.placer_type][self.args.mutation.lower()](self.args),
                crossover=OPS_REGISTRY["crossover"][self.placer_type][self.args.crossover.lower()](self.args),
                eliminate_duplicates=True
            )

            with gpytorch.settings.cholesky_jitter(1e-4):
                res = minimize(
                    problem=acqf_problem,
                    algorithm=algo,
                    termination=("n_gen", self.args.opt_acqf_iter),
                    verbose=False
                )
            
            proposed_X = res.pop.get("X")
            
        elif self.placer_type == "hpo" or self.placer_type == "mgo":
            normalized_bounds = torch.stack([torch.zeros(self.dim), torch.ones(self.dim)]).to(**tkwargs)
            with gpytorch.settings.cholesky_jitter(1e-4):
                proposed_X, _ = optimize_acqf(
                    acq_function=acqf,
                    bounds=normalized_bounds,
                    q=num_samples,
                    num_restarts=10,
                    raw_samples=512,
                    options={"batch_limit": 5, "maxiter": 200},
                    fixed_features=None,
                )
            proposed_X = unnormalize(proposed_X.detach(), self.bounds).cpu().numpy()
            
        else:
            raise NotImplementedError
        assert len(proposed_X) >= num_samples
        if len(proposed_X) > num_samples:
            indices = np.random.choice(proposed_X.shape[0], num_samples, replace=False)
            proposed_X = proposed_X[indices, :]
        
        hpwl, overlap_rate, macro_pos_all = self._get_observations(proposed_X, return_macro_pos=True)
        
        t_temp = time.time() 
        t_eval = t_temp - self.t 
        self.t_total += t_eval
        t_each_eval = t_eval / num_samples
        avg_t_each_eval = self.t_total / (self.n_eval + self.n_init)
        avg_t_eval_solution = self.placer.t_eval_solution_total / (self.n_eval + self.n_init)
        self.t = t_temp
        
        self._record_results(hpwl, overlap_rate, macro_pos_all,
                             t_each_eval=t_each_eval,
                             avg_t_each_eval=avg_t_each_eval,
                             avg_t_eval_solution=avg_t_eval_solution)
        
        return torch.from_numpy(proposed_X).to(**tkwargs), \
            torch.from_numpy(hpwl).to(**tkwargs)
        
    def run(self):
        self.t = time.time() 
        
        checkpoint = self._load_checkpoint()

        if checkpoint is not None:
            self.model_state_dict = checkpoint["model_state_dict"]
            self.train_X = checkpoint["train_X"].to(**tkwargs)
            self.train_Y = checkpoint["train_Y"].to(**tkwargs)
        else:
            self.train_X, self.train_Y = self._init_samples(n_samples=self.n_init)

        if len(self.train_X) < self.n_init:
            extended_X, extended_Y = self._init_samples(self.n_init - len(self.train_X))
            self.train_X = torch.cat((self.train_X, extended_X))
            self.train_Y = torch.cat((self.train_Y, extended_Y.reshape(-1, 1)))
              
        train_Y_tensor = deepcopy(self.train_Y)
        train_Y_tensor = (train_Y_tensor - train_Y_tensor.mean()) / (train_Y_tensor.std() + 1e-6)

        train_X_tensor = self.train_X
        if self.placer_type == "hpo" or self.placer_type == "mgo":
            train_X_tensor = normalize(self.train_X, self.bounds)

        self.model = self._init_model(train_X_tensor, train_Y_tensor,
                                      state_dict=self.model_state_dict if hasattr(self, "model_state_dict") \
                                          else None)
        
        # calculate how many batch
        n_batch = math.ceil((self.args.max_evals - self.n_init * (self.args.n_sampling_repeat-1) - \
            len(self.train_X)) / self.batch_size)
        
        for i in range(1, n_batch + 1):
            
            t0 = time.monotonic()
            
            acqf = self._get_acqf(self.acqf_type, self.model, train_X_tensor, train_Y_tensor)
            proposed_X, proposed_Y = self._optimize_acqf_and_get_observations(acqf, self.batch_size)
            
            assert len(proposed_X) == self.batch_size
            
            self.train_X = torch.cat((self.train_X, proposed_X))
            self.train_Y = torch.cat((self.train_Y, proposed_Y.reshape(-1, 1)))

            # De-duplicate training data for MGO placer
            if self.placer_type == "mgo":
                # Convert to integer coordinates to identify duplicates
                # This is necessary because continuous outputs from acqf optimization
                # can round to the same integer grid positions, causing duplicates.
                train_X_int = torch.round(self.train_X).cpu().numpy()
                _, unique_indices = np.unique(train_X_int, axis=0, return_index=True)
                
                if len(unique_indices) < self.train_X.shape[0]:
                    logging.info(f"Duplicate points found. Reducing dataset from {self.train_X.shape[0]} to {len(unique_indices)}")
                    # Keep only unique points
                    self.train_X = self.train_X[unique_indices]
                    self.train_Y = self.train_Y[unique_indices]
            
            self._save_checkpoint()
            
            train_Y_tensor = deepcopy(self.train_Y)
            train_Y_tensor = (train_Y_tensor - train_Y_tensor.mean()) / (train_Y_tensor.std() + 1e-6)
            
            train_X_tensor = self.train_X
            if self.placer_type == "hpo" or self.placer_type == "mgo":
                train_X_tensor = normalize(self.train_X, self.bounds)
            
            self.model = self._init_model(train_X_tensor, train_Y_tensor, self.model.state_dict())
            
            t1 = time.monotonic()
            
            if self.args.verbose:
                print(
                    f"\nBatch {i:>2}: best_hpwl = "
                    f"{self.best_hpwl}    "
                    f"time = {t1-t0:>4.2f}.",
                )
            else:
                print(".", end="")

    def _load_checkpoint(self):
        if hasattr(self.args, "checkpoint") and os.path.exists(self.args.checkpoint):
            super()._load_checkpoint()
            checkpoint_path = os.path.join(self.args.checkpoint, "saasbo.pt")
            checkpoint = torch.load(checkpoint_path)
            self.start_from_checkpoint = True
        else:
            checkpoint = None
            self.start_from_checkpoint = False
        
        return checkpoint
            
        
    def _save_checkpoint(self):
        super()._save_checkpoint()
        
        model_file = os.path.join(self.checkpoint_path, "saasbo.pt")
        self.model = self.model.to("cpu")
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "train_X": self.train_X.detach().cpu(),
            "train_Y": self.train_Y.detach().cpu(),
        }
        torch.save(obj=checkpoint, f=model_file)
        self.model = self.model.to(**tkwargs)

