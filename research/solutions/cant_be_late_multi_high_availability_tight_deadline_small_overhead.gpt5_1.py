import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_smart"

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
        self._committed_to_od = False
        self._last_region = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic state
        gap = float(self.env.gap_seconds)
        work_done = float(sum(self.task_done_time))
        remaining_work = max(0.0, float(self.task_duration) - work_done)
        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        overhead = float(self.restart_overhead)

        # Early termination
        if remaining_work <= 0.0:
            return ClusterType.NONE
        if remaining_time <= 0.0:
            # Past deadline, nothing to do
            return ClusterType.NONE

        # If we've already committed to OD, keep using it
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Compute conservative commit threshold
        # We require enough spare time to risk one more non-OD step:
        # remaining_time > remaining_work + overhead + gap
        # If not, we must commit to OD now.
        commit_threshold = remaining_work + overhead + gap

        # If currently on OD and no pending overhead, staying on OD avoids switch overhead;
        # adjust threshold slightly to avoid thrashing.
        if last_cluster_type == ClusterType.ON_DEMAND and getattr(self, "remaining_restart_overhead", 0.0) <= 1e-9:
            # Allow staying on OD if already tight
            commit_threshold = remaining_work + 0.5 * gap  # already on OD, less margin needed

        # Decide commitment to OD
        if remaining_time <= commit_threshold:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not yet committed to OD: prefer Spot when available
        if has_spot:
            # If we're currently on OD and far from deadline, consider switching to Spot only if slack is large
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Require ample slack to justify switch due to restart overhead
                slack = remaining_time - (remaining_work + overhead)
                # Need slack > 2*gap to safely switch to Spot
                if slack > 2.0 * gap:
                    return ClusterType.SPOT
                else:
                    # Keep OD to avoid overhead and risk
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot unavailable: decide between waiting and OD
        # If we still have sufficient slack to afford waiting this step, wait; else OD
        # Safe to wait if after waiting one gap, we still have time for work + overhead
        if (remaining_time - gap) > (remaining_work + overhead):
            return ClusterType.NONE

        # Otherwise, must use OD to ensure deadline
        self._committed_to_od = True
        return ClusterType.ON_DEMAND
