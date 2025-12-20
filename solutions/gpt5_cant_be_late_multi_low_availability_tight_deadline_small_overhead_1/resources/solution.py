import json
import random
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_rr_v2"

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
        self.od_committed = False
        self._num_regions = self.env.get_num_regions()
        self._rr_next = (self.env.get_current_region() + 1) % max(1, self._num_regions)
        # Guard time before deadline when we must ensure OD can finish safely
        self.guard_time = max(2.0 * self.env.gap_seconds, 6.0 * self.restart_overhead)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to OD, keep using it to avoid extra overheads.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self.od_committed = True
        if self.od_committed:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        work_remaining = max(0.0, self.task_duration - work_done)
        time_remaining = max(0.0, self.deadline - self.env.elapsed_seconds)

        # If already finished or nothing meaningful to do, pause
        if work_remaining <= 0.0 or time_remaining <= 0.0:
            return ClusterType.NONE

        # Estimate extra overhead if switching to OD now
        if last_cluster_type == ClusterType.ON_DEMAND:
            extra_overhead_if_od_now = self.remaining_restart_overhead
        else:
            # Worst-case: a full restart overhead if we switch to OD
            extra_overhead_if_od_now = self.restart_overhead

        # Time required to finish if we switch to OD now and stay
        od_time_needed = extra_overhead_if_od_now + work_remaining
        slack_if_od_now = time_remaining - od_time_needed

        # Decide whether we must commit to OD to meet the deadline
        # If spot is not available and waiting one more step makes OD infeasible with guard, commit now.
        if not has_spot:
            if slack_if_od_now - self.env.gap_seconds <= self.guard_time:
                self.od_committed = True
                return ClusterType.ON_DEMAND
        else:
            # If spot is available but we're too close to the deadline, commit to OD to avoid preemption risk.
            if slack_if_od_now <= self.guard_time:
                self.od_committed = True
                return ClusterType.ON_DEMAND

        # Not committing to OD now
        if has_spot:
            # Use spot when available
            return ClusterType.SPOT

        # Spot not available and we still have time to wait: try another region and wait one step
        if self._num_regions > 1:
            current = self.env.get_current_region()
            # Rotate regions to search for available spot
            next_region = self._rr_next
            if self._num_regions > 0:
                if next_region == current:
                    next_region = (current + 1) % self._num_regions
                self.env.switch_region(next_region)
                self._rr_next = (next_region + 1) % self._num_regions
        return ClusterType.NONE
