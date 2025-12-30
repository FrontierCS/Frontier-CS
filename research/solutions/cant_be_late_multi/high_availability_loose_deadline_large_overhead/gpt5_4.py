import json
from argparse import Namespace

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

        self.od_committed = False
        self._cached_done = 0.0
        self._last_done_len = 0
        return self

    def _update_cached_done(self):
        n = len(self.task_done_time)
        if n > self._last_done_len:
            # Sum only new segments
            self._cached_done += sum(self.task_done_time[self._last_done_len : n])
            self._last_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached work done in O(1) amortized time
        self._update_cached_done()

        # Remaining work and time
        remaining_work = max(0.0, self.task_duration - self._cached_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds
        if time_remaining <= 0.0:
            # Already out of time; try OD anyway
            return ClusterType.ON_DEMAND

        # If already committed to OD, stick with it to avoid extra overhead.
        if self.od_committed:
            return ClusterType.ON_DEMAND

        # Not committed yet: prefer SPOT when available; otherwise wait if slack allows, else commit to OD.

        # Overhead to start OD now (we are not committed, so assume switching to OD incurs a restart overhead)
        od_overhead_now = self.restart_overhead

        # Slack if we switch to OD now
        slack_to_od_now = time_remaining - (remaining_work + od_overhead_now)

        # If spot is available
        if has_spot:
            # If we are in a critical slack window and would incur an immediate overhead this step (due to pending restart),
            # avoid risking further slack loss by committing to OD now.
            if slack_to_od_now <= 0.0 and self.remaining_restart_overhead > 0.0:
                self.od_committed = True
                return ClusterType.ON_DEMAND
            # Otherwise, use SPOT
            return ClusterType.SPOT

        # Spot unavailable: wait if we still have positive slack to finish on OD later; else commit to OD now.
        if slack_to_od_now > 0.0:
            # Opportunistically scan to next region while waiting to increase chance of SPOT next step.
            try:
                num_regions = self.env.get_num_regions()
                if num_regions and num_regions > 1:
                    current = self.env.get_current_region()
                    self.env.switch_region((current + 1) % num_regions)
            except Exception:
                # In case environment methods are not available, safely ignore
                pass
            return ClusterType.NONE

        # No slack left to wait; commit to OD.
        self.od_committed = True
        return ClusterType.ON_DEMAND