import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_sched_v2"

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
        # Runtime state initialized lazily in _step
        return self

    def _lazy_init(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        # Safety margin: ensure enough buffer to switch to OD and handle discretization
        gap = getattr(self.env, "gap_seconds", 3600.0)
        self._safety_margin = max(gap, 2.0 * self.restart_overhead, 1800.0)  # at least 30 mins, typically >= gap
        self._panic_latched = False

        # Cumulative work cache to avoid O(n) sum at each step
        self._work_done_cache = sum(self.task_done_time)
        self._last_tdt_len = len(self.task_done_time)

        # Region rotation while waiting
        self._idle_steps = 0
        self._rotate_every = 1  # rotate region every waiting step
        self._num_regions = self.env.get_num_regions()
        self._region_spot_counts = [0] * self._num_regions
        self._region_seen_counts = [0] * self._num_regions

    def _update_work_done_cache(self):
        if len(self.task_done_time) > self._last_tdt_len:
            inc = sum(self.task_done_time[self._last_tdt_len:])
            self._work_done_cache += inc
            self._last_tdt_len = len(self.task_done_time)

    def _should_enter_panic(self, remaining_work: float, time_left: float) -> bool:
        # If we switch to OD now, we pay at most one restart_overhead.
        # Ensure we keep a safety margin to guard against discretization and decision latency.
        required_time = remaining_work + self.restart_overhead + self._safety_margin
        return time_left <= required_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update stats
        region = self.env.get_current_region()
        self._region_seen_counts[region] += 1
        if has_spot:
            self._region_spot_counts[region] += 1

        # Update cached work done
        self._update_work_done_cache()

        remaining_work = max(0.0, self.task_duration - self._work_done_cache)
        time_left = self.deadline - self.env.elapsed_seconds

        # If task is done or negative time (shouldn't happen), avoid spending
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Panic check and latch to ensure no deadline miss
        if not self._panic_latched and self._should_enter_panic(remaining_work, time_left):
            self._panic_latched = True

        if self._panic_latched:
            # Commit to On-Demand until finish; no region switches to avoid extra overhead
            return ClusterType.ON_DEMAND

        # Not in panic: favor Spot when available; otherwise, wait (NONE) and explore regions
        if has_spot:
            self._idle_steps = 0
            return ClusterType.SPOT

        # Spot not available: wait if there's still ample slack, optionally rotate region to explore
        self._idle_steps += 1
        if self._num_regions > 1 and (self._idle_steps % self._rotate_every == 0):
            next_region = (region + 1) % self._num_regions
            self.env.switch_region(next_region)

        return ClusterType.NONE
