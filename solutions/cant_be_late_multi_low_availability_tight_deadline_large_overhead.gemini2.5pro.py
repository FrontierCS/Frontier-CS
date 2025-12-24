import json
import math
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy based on dynamic programming.
    
    This strategy pre-computes the optimal plan in the `solve` method using
    dynamic programming, assuming full knowledge of spot availability traces.
    The `_step` method then simply executes the pre-computed plan.
    """

    NAME = "dp_optimizer"

    def _is_restart(self, prev_r, prev_l_idx, next_r, next_l_idx) -> bool:
        """Helper to determine if a transition incurs a restart overhead."""
        next_type = self.ct_map_rev[next_l_idx]
        if next_type == ClusterType.NONE:
            return False
        
        prev_type = self.ct_map_rev[prev_l_idx]
        if prev_type == ClusterType.NONE:
            return True
        if prev_r != next_r:
            return True
        if prev_l_idx != next_l_idx:
            return True
            
        return False

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
            trace_files=config["trace_files"]
        )
        super().__init__(args)

        self.spot_traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                self.spot_traces.append([bool(int(line.strip())) for line in f])
        
        PRICE_OD_PER_HR = 3.06
        PRICE_SPOT_PER_HR = 0.9701
        cost_od_step = PRICE_OD_PER_HR * self.env.gap_seconds / 3600.0
        cost_spot_step = PRICE_SPOT_PER_HR * self.env.gap_seconds / 3600.0
        
        gap_s = int(self.env.gap_seconds)
        duration_s = int(self.task_duration)
        overhead_s = int(self.restart_overhead)
        deadline_s = int(self.deadline)

        # Discretize time and work
        work_unit = math.gcd(math.gcd(gap_s, duration_s), overhead_s) if overhead_s > 0 else math.gcd(gap_s, duration_s)
        W_MAX = duration_s // work_unit
        T_MAX = deadline_s // gap_s
        R_MAX = self.env.get_num_regions()
        
        GAP_UNITS = gap_s // work_unit
        PROGRESS_RESTART_UNITS = (gap_s - overhead_s) // work_unit
        
        self.ct_map = {ClusterType.SPOT: 0, ClusterType.ON_DEMAND: 1, ClusterType.NONE: 2}
        self.ct_map_rev = {v: k for k, v in self.ct_map.items()}
        L_MAX = len(self.ct_map)

        dp = np.full((T_MAX + 1, W_MAX + 1, R_MAX, L_MAX), np.inf, dtype=np.float64)
        policy = np.full((T_MAX + 1, W_MAX + 1, R_MAX, L_MAX, 2), -1, dtype=np.int32)
        
        initial_region = 0
        initial_type_idx = self.ct_map[ClusterType.NONE]
        dp[0, 0, initial_region, initial_type_idx] = 0.0
        
        for t in range(T_MAX):
            if not self.spot_traces or t >= len(self.spot_traces[0]):
                break
            for w in range(W_MAX + 1):
                for r in range(R_MAX):
                    for l_idx in range(L_MAX):
                        if dp[t, w, r, l_idx] == np.inf:
                            continue

                        w_rem = W_MAX - w
                        t_rem = T_MAX - t
                        if w_rem > 0 and t_rem * GAP_UNITS < w_rem:
                            continue
                        
                        for next_r in range(R_MAX):
                            for next_l_idx in range(L_MAX):
                                next_type = self.ct_map_rev[next_l_idx]

                                if next_type == ClusterType.SPOT and not self.spot_traces[next_r][t]:
                                    continue
                                
                                step_cost = 0.0
                                if next_type == ClusterType.SPOT:
                                    step_cost = cost_spot_step
                                elif next_type == ClusterType.ON_DEMAND:
                                    step_cost = cost_od_step
                                
                                is_restart = self._is_restart(r, l_idx, next_r, next_l_idx)
                                progress = 0
                                if next_type != ClusterType.NONE:
                                    progress = PROGRESS_RESTART_UNITS if is_restart else GAP_UNITS
                                
                                new_w = min(W_MAX, w + progress)
                                new_cost = dp[t, w, r, l_idx] + step_cost
                                
                                if new_cost < dp[t + 1, new_w, next_r, next_l_idx]:
                                    dp[t + 1, new_w, next_r, next_l_idx] = new_cost
                                    policy[t + 1, new_w, next_r, next_l_idx] = [r, l_idx]

        best_cost = np.inf
        final_state = None
        # Find the earliest time the task can be completed with minimum cost
        for t in range(1, T_MAX + 1):
            if W_MAX < dp.shape[1] and t < dp.shape[0]:
                min_cost_at_t = np.min(dp[t, W_MAX, :, :])
                if min_cost_at_t < best_cost:
                    best_cost = min_cost_at_t
                    coords = np.argwhere(dp[t, W_MAX, :, :] == best_cost)[0]
                    final_state = (t, W_MAX, coords[0], coords[1])
        
        self.plan = []
        if final_state is not None:
            cur_t, cur_w, cur_r, cur_l_idx = final_state
            
            path = []
            while cur_t > 0:
                path.append((cur_r, self.ct_map_rev[cur_l_idx]))
                prev_r, prev_l_idx = policy[cur_t, cur_w, cur_r, cur_l_idx]
                
                is_restart = self._is_restart(prev_r, prev_l_idx, cur_r, cur_l_idx)
                progress = 0
                if self.ct_map_rev[cur_l_idx] != ClusterType.NONE:
                    progress = PROGRESS_RESTART_UNITS if is_restart else GAP_UNITS
                
                prev_w = cur_w - progress
                
                cur_t, cur_w, cur_r, cur_l_idx = cur_t - 1, prev_w, prev_r, prev_l_idx

            self.plan = list(reversed(path))
        else:
            self.plan = [(0, ClusterType.ON_DEMAND)] * T_MAX

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        
        if current_step >= len(self.plan):
            work_done = sum(self.task_done_time)
            if work_done < self.task_duration - 1e-6: # Float precision
                 return ClusterType.ON_DEMAND
            return ClusterType.NONE

        target_region, target_type = self.plan[current_step]

        if target_region != self.env.get_current_region():
            self.env.switch_region(target_region)

        return target_type
