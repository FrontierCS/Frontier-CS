import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "reliable_wait_spread"

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
        # Internal state
        self._ts_ready = False
        self._committed_to_on_demand = False
        return self

    def _init_ts_if_needed(self):
        if not getattr(self, "_ts_ready", False):
            n = 1
            try:
                n = int(self.env.get_num_regions())
            except Exception:
                n = 1
            self._n_regions = n
            self._alpha = [1.0] * n
            self._beta = [1.0] * n
            self._ts_ready = True

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Beta-Bernoulli updates
        if region_idx < 0 or region_idx >= self._n_regions:
            return
        if has_spot:
            self._alpha[region_idx] += 1.0
        else:
            self._beta[region_idx] += 1.0

    def _pick_best_region_ts(self, current_region: int) -> int:
        # Thompson sampling to select region with highest spot availability
        if self._n_regions <= 1:
            return current_region
        best_region = current_region
        best_sample = -1.0
        for i in range(self._n_regions):
            # sample from Beta posterior; slight stickiness to current region
            sample = random.betavariate(self._alpha[i], self._beta[i])
            if i == current_region:
                sample *= 1.02
            if sample > best_sample:
                best_sample = sample
                best_region = i
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_ts_if_needed()

        # If we ever start ON_DEMAND, treat as committed thereafter.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_on_demand = True

        current_region = 0
        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0

        # Update per-region availability stats with current observation.
        self._update_region_stats(current_region, has_spot)

        # Compute scheduling metrics
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remain = max(float(self.task_duration) - done, 0.0)
        time_left = max(float(self.deadline) - float(self.env.elapsed_seconds), 0.0)
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Small safety epsilon for SPOT commit decision (seconds)
        # Commit on SPOT when slack <= overhead + eps
        eps_spot = min(overhead * 0.25, gap * 0.25, 300.0)

        # If we already committed, always use ON_DEMAND to guarantee finish.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        slack = time_left - remain

        # If SPOT is available now, use it unless it's time to commit.
        if has_spot:
            # If slack is not enough to pay a restart overhead in worst-case,
            # commit to ON_DEMAND now.
            if slack <= overhead + eps_spot:
                self._committed_to_on_demand = True
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # SPOT unavailable: decide whether to wait (NONE) or commit to ON_DEMAND.
        # Safe to wait only if after waiting one time step, we still have enough time
        # to start ON_DEMAND and finish: slack - gap >= overhead.
        if slack > overhead + gap:
            # Wait and optionally switch to a better region according to TS.
            target_region = self._pick_best_region_ts(current_region)
            if target_region != current_region:
                try:
                    self.env.switch_region(target_region)
                except Exception:
                    pass
            return ClusterType.NONE

        # Not safe to wait further; commit to ON_DEMAND now.
        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND