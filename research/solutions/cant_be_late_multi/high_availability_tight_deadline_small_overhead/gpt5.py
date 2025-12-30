import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_multi_v1"

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
        return self

    # Internal initialization after env is ready
    def _lazy_init(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._od_lock = False
        self._no_spot_steps = 0
        self._switch_threshold = 2  # switch region after consecutive steps without spot
        self._alpha_prior = 2.0
        self._beta_prior = 1.0
        num_regions = self.env.get_num_regions()
        self._succ = [0] * num_regions
        self._tot = [0] * num_regions
        self._last_spot_time = [-1.0] * num_regions

    def _od_time_needed(self, remaining_work: float, from_cluster: ClusterType) -> float:
        # Time needed to finish if we commit to On-Demand now.
        # Includes initial restart overhead if we are not already on On-Demand.
        if remaining_work <= 0:
            return 0.0
        overhead = 0.0 if from_cluster == ClusterType.ON_DEMAND else self.restart_overhead
        step = self.env.gap_seconds
        return math.ceil((remaining_work + overhead) / step - 1e-12) * step

    def _best_region(self, current_region: int) -> int:
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return current_region
        now = self.env.elapsed_seconds
        best_idx = current_region
        # Compute score for each region: posterior mean availability with mild recency boost
        best_score = -1.0
        for r in range(num_regions):
            succ = self._succ[r]
            tot = self._tot[r]
            p_hat = (succ + self._alpha_prior) / (tot + self._alpha_prior + self._beta_prior)
            last_t = self._last_spot_time[r]
            recency = 0.0
            if last_t >= 0:
                # Boost if recently saw spot here; decay over 6 hours
                half_life = 6 * 3600.0
                age = max(0.0, now - last_t)
                recency = max(0.0, 1.0 - age / half_life)
            score = p_hat + 0.15 * recency
            if score > best_score:
                best_score = score
                best_idx = r
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update region stats with observation
        current_region = self.env.get_current_region()
        self._tot[current_region] += 1
        if has_spot:
            self._succ[current_region] += 1
            self._last_spot_time[current_region] = self.env.elapsed_seconds

        # Compute remaining work and time left
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        time_left = self.deadline - self.env.elapsed_seconds
        step = self.env.gap_seconds

        # If we must ensure completion, possibly lock to On-Demand
        if not self._od_lock:
            od_time_needed = self._od_time_needed(remaining_work, self.env.cluster_type)
            # If waiting one more step may cause us to run out of time, lock to On-Demand now
            if time_left <= od_time_needed + step:
                self._od_lock = True

        # If locked, always use On-Demand to guarantee finish
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            self._no_spot_steps = 0
            return ClusterType.SPOT

        # Spot unavailable in current region: consider switching region and wait (NONE)
        self._no_spot_steps += 1
        if self._no_spot_steps >= self._switch_threshold:
            best_region = self._best_region(current_region)
            if best_region != current_region:
                self.env.switch_region(best_region)
            self._no_spot_steps = 0

        return ClusterType.NONE