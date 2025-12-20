import json
from argparse import Namespace
from typing import List, Optional

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

        # Internal strategy state
        self._initialized = False
        self._commit_on_demand = False
        self._on_demand_region: Optional[int] = None
        self._region_scores: List[float] = []
        self._region_counts: List[float] = []
        self._region_success: List[float] = []
        self._no_spot_streak: List[int] = []
        self._last_switch_elapsed: float = 0.0
        self._cooldown_seconds: float = 0.0
        self._safe_margin_seconds: float = 0.0
        return self

    def _init_if_needed(self):
        if self._initialized:
            return
        num_regions = max(1, self.env.get_num_regions())
        # Initialize region statistics with a mild prior (Beta(1,1) -> 0.5)
        self._region_scores = [0.5 for _ in range(num_regions)]
        self._region_counts = [2.0 for _ in range(num_regions)]  # prior count
        self._region_success = [1.0 for _ in range(num_regions)]  # prior success
        self._no_spot_streak = [0 for _ in range(num_regions)]
        self._last_switch_elapsed = self.env.elapsed_seconds
        # Cooldown: avoid rapid switching thrash; though strategy minimizes switches already
        self._cooldown_seconds = self.env.gap_seconds * 2.0
        # Safety margin: account for discretization and overhead consumption granularity
        self._safe_margin_seconds = max(self.env.gap_seconds * 0.5, self.restart_overhead)
        self._initialized = True

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Update simple sample mean estimate
        self._region_counts[region_idx] += 1.0
        if has_spot:
            self._region_success[region_idx] += 1.0
            self._no_spot_streak[region_idx] = 0
        else:
            self._no_spot_streak[region_idx] += 1
        self._region_scores[region_idx] = self._region_success[region_idx] / self._region_counts[region_idx]

    def _compute_remaining(self) -> float:
        return max(0.0, self.task_duration - sum(self.task_done_time))

    def _must_commit_on_demand(self) -> bool:
        remaining = self._compute_remaining()
        time_left = self.deadline - self.env.elapsed_seconds
        # If we switch to on-demand now and never stop, we need restart_overhead + remaining time.
        # We add a small safety margin to avoid discretization misses.
        required = self.restart_overhead + remaining + self._safe_margin_seconds
        return time_left <= required

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()

        current_region = self.env.get_current_region()
        # Update stats with current observation
        self._update_region_stats(current_region, has_spot)

        # If we've already committed to on-demand, keep running it to avoid extra overhead
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Check if we must switch to on-demand to guarantee deadline
        if self._must_commit_on_demand():
            self._commit_on_demand = True
            self._on_demand_region = current_region
            return ClusterType.ON_DEMAND

        # We are still in the "spot-first" phase.
        # If spot is available now, use it.
        if has_spot:
            # Prefer to stay in current region to avoid any potential region-switch overhead semantics.
            return ClusterType.SPOT

        # Spot not available now. We can pause if we still have slack.
        # Decide whether we can afford to idle for one step safely.
        remaining = self._compute_remaining()
        time_left = self.deadline - self.env.elapsed_seconds
        # If we idle one gap, the time left reduces by gap_seconds. After idling, we can still finish by
        # switching to on-demand for remaining time with one restart overhead.
        time_left_after_idle = time_left - self.env.gap_seconds
        required_after_idle = self.restart_overhead + remaining + self._safe_margin_seconds
        if time_left_after_idle > required_after_idle:
            # We can safely idle and wait for spot later.
            return ClusterType.NONE

        # Not enough slack to idle this entire step; commit to on-demand now.
        self._commit_on_demand = True
        self._on_demand_region = current_region
        return ClusterType.ON_DEMAND
