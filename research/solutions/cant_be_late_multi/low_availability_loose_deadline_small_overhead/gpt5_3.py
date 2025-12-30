import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_heuristic"

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

        # Internal initialization
        self._rng = random.Random(42)
        self._committed_on_demand = False
        self._cached_task_done_total = 0.0
        self._cached_task_done_len = 0

        # Region stats (lazy init in _step because env might not be fully set up before)
        self._regions_inited = False
        self._region_S = []
        self._region_F = []
        self._region_obs = []
        return self

    def _lazy_init_regions(self):
        if not self._regions_inited:
            n = self.env.get_num_regions()
            self._region_S = [1.0] * n  # Beta prior alpha
            self._region_F = [1.0] * n  # Beta prior beta
            self._region_obs = [0] * n
            self._regions_inited = True

    def _update_task_done_cache(self):
        # Efficiently maintain sum of task_done_time
        l = len(self.task_done_time)
        if l > self._cached_task_done_len:
            for i in range(self._cached_task_done_len, l):
                self._cached_task_done_total += self.task_done_time[i]
            self._cached_task_done_len = l

    def _choose_region(self):
        # Epsilon-greedy on estimated spot availability
        n = len(self._region_S)
        # Compute estimate
        estimates = []
        for i in range(n):
            a = self._region_S[i]
            b = self._region_F[i]
            estimates.append(a / (a + b))
        # Epsilon
        epsilon = 0.1
        if self._rng.random() < epsilon:
            return self._rng.randrange(n)
        # Greedy
        best_idx = 0
        best_val = -1.0
        for i in range(n):
            v = estimates[i]
            if v > best_val:
                best_val = v
                best_idx = i
        return best_idx

    def _should_commit_to_on_demand(self, last_cluster_type: ClusterType, time_left: float, remaining_work: float) -> bool:
        # Small safety fudge
        fudge = 60.0  # seconds
        overhead_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return time_left <= remaining_work + overhead_switch + fudge

    def _safe_to_idle_one_step(self, time_left: float, remaining_work: float) -> bool:
        # After idling one step, we still need enough time to finish with ON_DEMAND
        # Assume we'll need to pay restart overhead upon starting ON_DEMAND.
        fudge = 60.0  # seconds
        return time_left >= remaining_work + self.restart_overhead + self.env.gap_seconds + fudge

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init_regions()

        # Update per-region observation with current region and current has_spot
        current_region = self.env.get_current_region()
        self._region_obs[current_region] += 1
        if has_spot:
            self._region_S[current_region] += 1.0
        else:
            self._region_F[current_region] += 1.0

        # Update work done cache
        self._update_task_done_cache()

        time_left = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - self._cached_task_done_total

        # If already committed, stay on ON_DEMAND
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # If time is tight, commit to ON_DEMAND now
        if self._should_commit_to_on_demand(last_cluster_type, time_left, remaining_work):
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available: decide to idle or start ON_DEMAND
        if self._safe_to_idle_one_step(time_left, remaining_work):
            # Switch to best region while idling to increase chance of SPOT next step
            target_region = self._choose_region()
            if target_region != current_region:
                self.env.switch_region(target_region)
            return ClusterType.NONE
        else:
            # Not safe to idle; start ON_DEMAND and commit to it
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND