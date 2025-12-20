An optimal scheduling strategy based on Dynamic Programming.

The strategy works as follows:
1.  In the `solve` method, which is called once at the beginning, we
    pre-compute an optimal plan for the entire duration up to the deadline.
2.  This is possible because we are given the full spot availability traces
    for all regions in advance.
3.  The problem is modeled as finding the shortest path in a state graph,
    which is solved efficiently using dynamic programming.
4.  The time and work are discretized into coarse steps, with the size of
    a coarse step being equal to the restart overhead time. This makes the
    DP state space manageable.
5.  The DP state is defined as `(time_step, work_done, region, cluster_type)`,
    and the DP table stores the minimum cost to reach each state.
6.  After the DP table is computed, we find the plan that completes the
    required work by the deadline with the minimum cost.
7.  This plan is reconstructed by backtracking through the DP policy table.
8.  The `_step` method, called at each time step of the simulation, simply
    looks up the pre-computed action for the current time step from the
    plan and executes it (i.e., switches region if necessary and returns
    the chosen cluster type).
9.  A fallback mechanism is implemented in `_step` to handle deviations
    from the plan, for example, if the plan prescribes using a spot
    instance but it's unavailable in reality. In such cases, it makes a
    safe choice (On-Demand or None) based on the urgency to finish.
"""

import json
import math
import numpy as np
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "dp_optimizer"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution and pre-compute the optimal plan."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Prices from problem description
        self.spot_price_per_hr = 0.9701
        self.ondemand_price_per_hr = 3.06

        self.spot_traces = [np.array(json.load(open(p))) for p in config['trace_files']]
        self.num_regions = len(self.spot_traces)

        # DP parameters using restart_overhead as the coarse time step `d_t`
        self.d_t = self.restart_overhead
        if self.d_t == 0:
            self.d_t = 3600.0 if self.deadline > 0 else 1.0

        # This assumes restart_overhead is a multiple of gap_seconds
        self.steps_per_coarse = int(round(self.d_t / self.gap_seconds))

        T_coarse = int(self.deadline / self.d_t)
        W_coarse = int(self.task_duration / self.d_t)

        self.preprocess_spot_traces(T_coarse)
        self.run_dp(T_coarse, W_coarse)
        self.reconstruct_plan(T_coarse, W_coarse)

        return self

    def preprocess_spot_traces(self, T_coarse: int):
        """Aggregate fine-grained spot traces into coarse-grained ones."""
        num_fine_steps = len(self.spot_traces[0]) if self.spot_traces else 0
        self.coarse_spot_traces = np.zeros((self.num_regions, T_coarse), dtype=bool)
        for r in range(self.num_regions):
            trace = self.spot_traces[r]
            for k in range(T_coarse):
                start_idx = k * self.steps_per_coarse
                end_idx = (k + 1) * self.steps_per_coarse
                if start_idx >= num_fine_steps:
                    break
                # A coarse step is spot-available only if spot is available throughout.
                self.coarse_spot_traces[r, k] = np.all(trace[start_idx:end_idx])

    def run_dp(self, T_coarse: int, W_coarse: int):
        """Execute the dynamic programming algorithm to find the optimal policy."""
        SPOT_I, OD_I, NONE_I = 0, 1, 2
        
        cost_per_step = {
            SPOT_I: self.spot_price_per_hr * self.d_t / 3600.0,
            OD_I: self.ondemand_price_per_hr * self.d_t / 3600.0,
            NONE_I: 0.0,
        }

        self.cost_table = np.full((T_coarse + 1, self.num_regions, 3), np.inf)
        self.work_table = np.full((T_coarse + 1, self.num_regions, 3), -1)
        self.policy_table = np.zeros((T_coarse + 1, self.num_regions, 3, 2), dtype=int)

        for r in range(self.num_regions):
            self.cost_table[0, r, NONE_I] = 0
            self.work_table[0, r, NONE_I] = 0

        for k in range(T_coarse):
            for r_prev in range(self.num_regions):
                for type_prev in range(3):
                    if np.isinf(self.cost_table[k, r_prev, type_prev]):
                        continue
                    
                    current_cost = self.cost_table[k, r_prev, type_prev]
                    current_work = self.work_table[k, r_prev, type_prev]

                    for r_curr in range(self.num_regions):
                        for type_curr in range(3):
                            if type_curr == SPOT_I and not self.coarse_spot_traces[r_curr, k]:
                                continue

                            next_cost = current_cost + cost_per_step[type_curr]
                            
                            incurs_overhead = False
                            is_working_type = type_curr in (SPOT_I, OD_I)
                            was_working_type = type_prev in (SPOT_I, OD_I)
                            if is_working_type:
                                if not was_working_type or r_curr != r_prev or type_curr != type_prev:
                                    incurs_overhead = True

                            work_done = 1 if is_working_type and not incurs_overhead else 0
                            next_work = current_work + work_done

                            if next_cost < self.cost_table[k + 1, r_curr, type_curr] or \
                               (math.isclose(next_cost, self.cost_table[k + 1, r_curr, type_curr]) and \
                                next_work > self.work_table[k + 1, r_curr, type_curr]):
                                self.cost_table[k + 1, r_curr, type_curr] = next_cost
                                self.work_table[k + 1, r_curr, type_curr] = next_work
                                self.policy_table[k + 1, r_curr, type_curr] = [r_prev, type_prev]

    def reconstruct_plan(self, T_coarse: int, W_coarse: int):
        """Backtrack through the policy table to build the final plan."""
        best_cost = np.inf
        final_state = None

        for k in range(1, T_coarse + 1):
            if np.any(self.work_table[k] >= W_coarse):
                costs = self.cost_table[k]
                valid_costs = np.where(self.work_table[k] >= W_coarse, costs, np.inf)
                min_cost_k = np.min(valid_costs)
                if min_cost_k < best_cost:
                    best_cost = min_cost_k
                    loc = np.argwhere(valid_costs == min_cost_k)[0]
                    final_state = (k, loc[0], loc[1])
        
        if final_state is None:
            self.plan = [(0, 1)] * T_coarse 
            return

        k_final, r_final, type_final = final_state
        plan_rev = []
        
        curr_k, curr_r, curr_type = k_final, r_final, type_final
        while curr_k > 0:
            plan_rev.append((curr_r, curr_type))
            prev_r, prev_type = self.policy_table[curr_k, curr_r, curr_type]
            curr_r, curr_type = prev_r, prev_type
            curr_k -= 1

        self.plan = list(reversed(plan_rev))

        final_region = self.plan[-1][0] if self.plan else 0
        while len(self.plan) < T_coarse:
            self.plan.append((final_region, 2))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        if not hasattr(self, 'plan'):
            return ClusterType.ON_DEMAND

        current_k = int(self.env.elapsed_seconds / self.d_t)

        if current_k >= len(self.plan):
            return ClusterType.NONE

        planned_region, planned_type_idx = self.plan[current_k]
        
        type_map = {0: ClusterType.SPOT, 1: ClusterType.ON_DEMAND, 2: ClusterType.NONE}
        planned_type = type_map[planned_type_idx]

        if self.env.get_current_region() != planned_region:
            self.env.switch_region(planned_region)

        if planned_type == ClusterType.SPOT and not has_spot:
            work_left = self.task_duration - sum(self.task_done_time)
            time_left = self.deadline - self.env.elapsed_seconds
            
            time_needed_od = work_left + self.restart_overhead
            
            if time_left <= time_needed_od + self.restart_overhead:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

        return planned_type
