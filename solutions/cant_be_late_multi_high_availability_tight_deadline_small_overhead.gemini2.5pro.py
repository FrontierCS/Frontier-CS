import json
from argparse import Namespace
import math
import numpy as np

# Use try-except for local testing without the full sky_spot package
try:
    from sky_spot.strategies.multi_strategy import MultiRegionStrategy
    from sky_spot.utils import ClusterType
except ImportError:
    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"

    class MultiRegionStrategy:
        def __init__(self, args):
            self.task_duration = args.task_duration_hours[0] * 3600
            self.deadline = args.deadline_hours * 3600
            self.restart_overhead = args.restart_overhead_hours[0] * 3600
            self.env = None

        def solve(self, spec_path: str):
            raise NotImplementedError

        def _step(self, last_cluster_type: ClusterType, has_spot: bool):
            raise NotImplementedError


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy using Dynamic Programming.
    
    The strategy pre-computes the optimal plan in the `solve` method
    based on the provided spot availability traces. The `_step` method
    then executes this pre-computed plan at each time step.
    """

    NAME = "dp_solver"

    # Based on problem parameters (task duration, deadline, overhead), which are
    # all multiples of 0.05 hours (180 seconds), we assume the simulation time
    # step (gap_seconds) is 180 seconds. This is a critical assumption for the
    # DP formulation.
    ASSUMED_GAP_SECONDS = 180.0
    
    # Prices from problem description
    SPOT_PRICE_PER_HR = 0.9701
    OD_PRICE_PER_HR = 3.06

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution and pre-compute the optimal plan using DP.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self.num_regions = len(config["trace_files"])
        self.spot_traces = self._load_traces(config["trace_files"])
        
        self._precompute_plan()

        return self

    def _load_traces(self, trace_files: list[str]) -> np.ndarray:
        """
        Load spot availability traces from files.
        Assumes each file contains a sequence of '0' or '1' strings,
        one per line, corresponding to each time step.
        """
        traces = []
        for trace_file in trace_files:
            with open(trace_file) as f:
                # Using np.fromiter for efficient parsing of large files
                trace_data = np.fromiter((line.strip() for line in f), dtype=np.int8)
                traces.append(trace_data == 1)
        return np.array(traces)

    def _precompute_plan(self):
        """
        Uses dynamic programming to find the cost-optimal plan that meets the deadline.
        The plan is stored as a sequence of actions for each time step.
        """
        # Discretize problem parameters based on the assumed time step duration
        W_total = int(round(self.task_duration / self.ASSUMED_GAP_SECONDS))
        T_deadline = int(round(self.deadline / self.ASSUMED_GAP_SECONDS))
        O_steps = int(math.ceil(self.restart_overhead / self.ASSUMED_GAP_SECONDS))
        
        spot_price_per_step = (self.SPOT_PRICE_PER_HR / 3600) * self.ASSUMED_GAP_SECONDS
        od_price_per_step = (self.OD_PRICE_PER_HR / 3600) * self.ASSUMED_GAP_SECONDS

        # Precompute the next time step with available spot for each region and time
        num_timesteps = self.spot_traces.shape[1]
        next_spot = np.full((self.num_regions, num_timesteps + 1), T_deadline, dtype=int)
        for r in range(self.num_regions):
            for t in range(num_timesteps - 1, -1, -1):
                if self.spot_traces[r, t]:
                    next_spot[r, t] = t
                else:
                    next_spot[r, t] = next_spot[r, t + 1]

        # DP state: dp[w][r] = (min_cost, finish_time) to complete w work units, ending in region r.
        dp = np.full((W_total + 1, self.num_regions, 2), np.inf)
        
        # Policy stores the decision that led to the optimal state:
        # policy[(w, r)] = (prev_region, action_type, work_start_time, work_finish_time)
        policy = {}

        # Base case: 0 work done costs 0 and takes 0 time.
        dp[0, :, 0] = 0.0
        dp[0, :, 1] = 0

        for w in range(W_total):
            for r_prev in range(self.num_regions):
                cost, time = dp[w, r_prev]
                if not np.isfinite(time):
                    continue
                time_int = int(time)

                # Option 1: Stay in r_prev
                # 1a: Use Spot
                t_start_spot = next_spot[r_prev, time_int]
                if t_start_spot < T_deadline:
                    t_finish_spot = t_start_spot + 1
                    new_cost_spot = cost + spot_price_per_step
                    if new_cost_spot < dp[w + 1, r_prev, 0] or \
                       (new_cost_spot == dp[w + 1, r_prev, 0] and t_finish_spot < dp[w + 1, r_prev, 1]):
                        dp[w + 1, r_prev] = [new_cost_spot, t_finish_spot]
                        policy[(w + 1, r_prev)] = (r_prev, 'SPOT', t_start_spot, t_finish_spot)

                # 1b: Use On-Demand
                t_start_od = time_int
                t_finish_od = t_start_od + 1
                if t_finish_od <= T_deadline:
                    new_cost_od = cost + od_price_per_step
                    if new_cost_od < dp[w + 1, r_prev, 0] or \
                       (new_cost_od == dp[w + 1, r_prev, 0] and t_finish_od < dp[w + 1, r_prev, 1]):
                        dp[w + 1, r_prev] = [new_cost_od, t_finish_od]
                        policy[(w + 1, r_prev)] = (r_prev, 'OD', t_start_od, t_finish_od)
                
                # Option 2: Switch from r_prev to r_curr
                time_after_switch = time_int + O_steps
                for r_curr in range(self.num_regions):
                    if r_curr == r_prev: continue
                    
                    # 2a: Use Spot in r_curr after switching
                    t_start_spot = next_spot[r_curr, time_after_switch]
                    if t_start_spot < T_deadline:
                        t_finish_spot = t_start_spot + 1
                        new_cost_spot = cost + spot_price_per_step
                        if new_cost_spot < dp[w + 1, r_curr, 0] or \
                           (new_cost_spot == dp[w + 1, r_curr, 0] and t_finish_spot < dp[w + 1, r_curr, 1]):
                            dp[w + 1, r_curr] = [new_cost_spot, t_finish_spot]
                            policy[(w + 1, r_curr)] = (r_prev, 'SWITCH_SPOT', t_start_spot, t_finish_spot)

                    # 2b: Use On-Demand in r_curr after switching
                    t_start_od = time_after_switch
                    t_finish_od = t_start_od + 1
                    if t_finish_od <= T_deadline:
                        new_cost_od = cost + od_price_per_step
                        if new_cost_od < dp[w + 1, r_curr, 0] or \
                           (new_cost_od == dp[w + 1, r_curr, 0] and t_finish_od < dp[w + 1, r_curr, 1]):
                            dp[w + 1, r_curr] = [new_cost_od, t_finish_od]
                            policy[(w + 1, r_curr)] = (r_prev, 'SWITCH_OD', t_start_od, t_finish_od)

        # Backtrack from the best final state to build the time-step plan
        best_final_r = np.argmin(dp[W_total, :, 0])
        final_cost = dp[W_total, best_final_r, 0]

        if not np.isfinite(final_cost):
            self.plan_failed = True
            return
        self.plan_failed = False

        plan = [(ClusterType.NONE, 0)] * T_deadline
        w, r = W_total, best_final_r
        
        while w > 0:
            r_prev, action_type, t_start, _ = policy[(w, r)]
            work_type = ClusterType.SPOT if 'SPOT' in action_type else ClusterType.ON_DEMAND
            plan[t_start] = (work_type, r)
            
            prev_finish_time = int(dp[w - 1, r_prev, 1])
            
            fill_region = r if 'SWITCH' in action_type else r_prev
            for t in range(prev_finish_time, t_start):
                plan[t] = (ClusterType.NONE, fill_region)
            
            w, r = w - 1, r_prev
            
        current_region = 0
        for t in range(T_deadline):
            action, region = plan[t]
            if region != 0:
                current_region = region
            elif action == ClusterType.NONE:
                plan[t] = (ClusterType.NONE, current_region)

        self.time_step_plan = plan


    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action based on the pre-computed plan.
        """
        if self.plan_failed or not hasattr(self, 'time_step_plan'):
            return ClusterType.ON_DEMAND

        current_time_step = int(self.env.elapsed_seconds / self.ASSUMED_GAP_SECONDS)
        
        if current_time_step >= len(self.time_step_plan):
            return ClusterType.NONE if sum(self.task_done_time) >= self.task_duration else ClusterType.ON_DEMAND

        planned_action, planned_region = self.time_step_plan[current_time_step]

        if self.env.get_current_region() != planned_region:
            self.env.switch_region(planned_region)

        if planned_action == ClusterType.SPOT:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
        else:
            return planned_action
