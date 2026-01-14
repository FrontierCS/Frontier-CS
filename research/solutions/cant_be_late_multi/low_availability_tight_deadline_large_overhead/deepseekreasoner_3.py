import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Fixed parameters (assumed from problem statement)
        self.gap_seconds = 3600.0
        self.overhead_seconds = float(config["overhead"]) * 3600.0
        self.task_duration_seconds = float(config["duration"]) * 3600.0
        self.deadline_seconds = float(config["deadline"]) * 3600.0
        self.T = int(self.deadline_seconds / self.gap_seconds)  # 36 steps

        # Discretization unit = overhead (720 seconds)
        self.unit = self.overhead_seconds
        self.gap_units = int(self.gap_seconds / self.unit)          # 5
        self.overhead_units = 1
        self.task_units = int(self.task_duration_seconds / self.unit)  # 120

        # Load spot availability traces
        self.avail = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                lines = f.readlines()
            region_avail = []
            for i in range(self.T):
                line = lines[i].strip()
                region_avail.append(line == "1")
            self.avail.append(region_avail)
        self.num_regions = len(self.avail)

        # Precompute optimal policy via dynamic programming
        self._compute_policy()

        return self

    def _compute_policy(self):
        """Compute DP table and store optimal actions."""
        T = self.T
        R = self.num_regions
        W = self.task_units + 1   # work states 0..task_units

        # Cost per step (in dollars) for each cluster type
        cost_spot = 0.9701
        cost_ondemand = 3.06
        cost_none = 0.0

        # DP cost table: dimensions [T+1][R][3][W]
        INF = 1e9
        cost = [[[[INF for _ in range(W)] for _ in range(3)] for _ in range(R)] for _ in range(T+1)]
        # Action table: store (next_region, next_cluster_int)
        action = [[[[None for _ in range(W)] for _ in range(3)] for _ in range(R)] for _ in range(T+1)]

        # Base case at t = T (deadline)
        for r in range(R):
            for c in range(3):
                cost[T][r][c][self.task_units] = 0.0

        # Backward DP
        for t in range(T-1, -1, -1):
            for r in range(R):
                for c in range(3):
                    for w in range(self.task_units + 1):
                        best_cost = INF
                        best_action = None
                        # Consider all possible next regions and cluster types
                        for r2 in range(R):
                            for a_int in range(3):  # 0=NONE, 1=SPOT, 2=ON_DEMAND
                                if a_int == 1 and not self.avail[r2][t]:
                                    continue
                                # Cost for this step
                                if a_int == 0:
                                    step_cost = cost_none
                                    work_units = 0
                                else:
                                    if a_int == 1:
                                        step_cost = cost_spot
                                    else:  # a_int == 2
                                        step_cost = cost_ondemand
                                    # Check if restart overhead applies
                                    if r2 != r or a_int != c:
                                        work_units = self.gap_units - self.overhead_units  # 4
                                    else:
                                        work_units = self.gap_units  # 5
                                new_w = min(self.task_units, w + work_units)
                                future_cost = cost[t+1][r2][a_int][new_w]
                                total = step_cost + future_cost
                                if total < best_cost:
                                    best_cost = total
                                    best_action = (r2, a_int)
                        cost[t][r][c][w] = best_cost
                        action[t][r][c][w] = best_action

        self.action_table = action

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current time step index (number of steps already taken)
        t = int(self.env.elapsed_seconds / self.env.gap_seconds)
        if t >= self.T:
            return ClusterType.NONE

        # Current region
        current_region = self.env.get_current_region()

        # Convert last_cluster_type to integer code
        if last_cluster_type == ClusterType.NONE:
            c = 0
        elif last_cluster_type == ClusterType.SPOT:
            c = 1
        else:  # ON_DEMAND
            c = 2

        # Compute work done so far in units
        total_work_seconds = sum(self.task_done_time)
        w = int(round(total_work_seconds / self.unit))
        w = min(w, self.task_units)

        # If already finished, do nothing
        if w >= self.task_units:
            return ClusterType.NONE

        # Look up optimal action
        action = self.action_table[t][current_region][c][w]
        if action is None:
            # Should not happen if DP is correct, but fallback
            return ClusterType.ON_DEMAND

        next_region, next_a_int = action

        # Switch region if needed
        if next_region != current_region:
            self.env.switch_region(next_region)

        # Convert back to ClusterType
        if next_a_int == 0:
            return ClusterType.NONE
        elif next_a_int == 1:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND