import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cb_late_multiregion_v1"

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

        # Internal state initialization
        self._initialized = False
        self._committed_od = False
        self._alpha = 2.0
        self._beta = 2.0
        self._region_success = []
        self._region_total = []
        self._progress_done_sec = 0.0
        self._last_task_done_len = 0
        self._target_region = None
        # slight randomness for tie-breaking
        self._rand = random.Random(0xC0FFEE)
        return self

    def _init_regions(self):
        n = self.env.get_num_regions()
        self._region_success = [0] * n
        self._region_total = [0] * n
        self._initialized = True

    def _update_progress_cache(self):
        # Incrementally update completed work sum to avoid O(n) each step
        done_list = self.task_done_time
        if len(done_list) > self._last_task_done_len:
            # sum only new entries
            delta = 0.0
            for i in range(self._last_task_done_len, len(done_list)):
                delta += done_list[i]
            self._progress_done_sec += delta
            self._last_task_done_len = len(done_list)

    def _best_region(self):
        # Choose region with highest posterior mean availability
        n = self.env.get_num_regions()
        best_idx = 0
        best_score = -1.0
        for r in range(n):
            tot = self._region_total[r]
            suc = self._region_success[r]
            score = (suc + self._alpha) / (tot + self._alpha + self._beta)
            # Slight random tie-breaker
            score += 1e-8 * self._rand.random()
            if score > best_score:
                best_score = score
                best_idx = r
        return best_idx

    def _should_bail_to_od(self, last_cluster_type):
        # Compute conservative time threshold for bailing to on-demand
        # Remaining work and time left
        current_time = self.env.elapsed_seconds
        time_left = max(0.0, self.deadline - current_time)
        remaining_work = max(0.0, self.task_duration - self._progress_done_sec)

        # If already committed, always bail
        if self._committed_od:
            return True

        # If already on OD and continue, no new overhead; otherwise, pay restart overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_if_bail_now = 0.0
        else:
            overhead_if_bail_now = self.restart_overhead

        # Conservative buffer to account for step granularity and edge cases
        # Use at least 10 minutes or 1 step, whichever is larger, plus a small overhead buffer
        base_buffer = max(self.env.gap_seconds, 600.0)
        buffer = base_buffer + 0.5 * self.restart_overhead

        required_time_on_od = remaining_work + overhead_if_bail_now

        return time_left <= (required_time_on_od + buffer)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._init_regions()

        # Update per-step observations for current region
        cur_region = self.env.get_current_region()
        # Track spot availability observations even if we don't use spot
        if 0 <= cur_region < len(self._region_total):
            self._region_total[cur_region] += 1
            if has_spot:
                self._region_success[cur_region] += 1

        # Keep incremental progress cache up to date
        self._update_progress_cache()

        # If task already completed, no need to run
        if self._progress_done_sec >= self.task_duration:
            return ClusterType.NONE

        # Decide if we must commit to on-demand to ensure deadline
        if self._should_bail_to_od(last_cluster_type):
            self._committed_od = True
            # Once committed, never switch back to spot
            return ClusterType.ON_DEMAND

        # Try to use spot when available in current region
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region and we haven't committed to OD:
        # Move to the region with the highest estimated availability and wait
        best_r = self._best_region()
        if best_r != cur_region:
            self.env.switch_region(best_r)
        return ClusterType.NONE