import json
import math
from argparse import Namespace
from typing import List

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

        # Runtime vars initialized lazily in first _step
        self._initialized_runtime = False
        self._od_committed = False  # Once true, always run on-demand to guarantee finish
        self._ucb_c = 0.35  # Exploration weight for choosing regions
        self._prior_a = 1.0  # Beta prior for availability
        self._prior_b = 1.0
        self._last_region = None
        return self

    def _init_runtime(self):
        if self._initialized_runtime:
            return
        # Initialize region stats
        self._num_regions = self.env.get_num_regions()
        self._region_counts: List[int] = [0 for _ in range(self._num_regions)]
        self._region_success: List[int] = [0 for _ in range(self._num_regions)]
        self._total_samples = 0
        self._step_idx = 0
        self._initialized_runtime = True

    def _remaining_work_seconds(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - done)
        return remaining

    def _dynamic_buffer(self, last_cluster_type: ClusterType) -> float:
        # End-game safety buffer: cover a few overheads and some step granularity.
        # Conservative to prevent missing deadlines.
        step = getattr(self.env, "gap_seconds", 300.0)
        base = max(2.0 * self.restart_overhead, 1.0 * step)
        # If we are not currently on ON_DEMAND, add a small extra cushion to account for a potential switch.
        if last_cluster_type != ClusterType.ON_DEMAND:
            base += 0.5 * step
        return base

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        self._region_counts[region_idx] += 1
        if has_spot:
            self._region_success[region_idx] += 1
        self._total_samples += 1

    def _best_region_by_score(self, current_region: int) -> int:
        # UCB-style scoring with Beta prior to encourage exploration across regions
        total = max(1, self._total_samples)
        best_idx = current_region
        best_score = -1.0
        for i in range(self._num_regions):
            n = self._region_counts[i]
            s = self._region_success[i]
            mean = (s + self._prior_a) / (n + self._prior_a + self._prior_b)
            ucb = self._ucb_c * math.sqrt(math.log(total + 1.0) / (n + 1.0))
            score = mean + ucb
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _should_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        remaining_work = self._remaining_work_seconds()
        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_work <= 0.0:
            return False
        # Overhead to switch to ON_DEMAND (0 if already on ON_DEMAND)
        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        buffer_time = self._dynamic_buffer(last_cluster_type)
        # If not enough time to safely wait, commit to ON_DEMAND
        return remaining_time <= (remaining_work + od_overhead + buffer_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()
        self._step_idx += 1
        current_region = self.env.get_current_region()

        # Track observed spot availability for current region
        self._update_region_stats(current_region, has_spot)

        # Check if we need to commit to ON_DEMAND to avoid missing the deadline
        if not self._od_committed and self._should_commit_on_demand(last_cluster_type):
            self._od_committed = True

        if self._od_committed:
            # Once committed, always run on-demand to guarantee completion
            return ClusterType.ON_DEMAND

        # If SPOT is available now in this region, use it
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available; we have slack (since not committed).
        # Prefer waiting for SPOT to save cost.
        # Optionally switch to a region that historically has higher availability to prepare for next step.
        # Do not switch regions if we plan to return SPOT immediately in this step (we are not).
        # Also avoid switching while running ON_DEMAND (not committed) to prevent unnecessary restarts.
        if last_cluster_type != ClusterType.ON_DEMAND:
            target_region = self._best_region_by_score(current_region)
            if target_region != current_region:
                self.env.switch_region(target_region)

        # Wait this step to preserve budget
        return ClusterType.NONE
