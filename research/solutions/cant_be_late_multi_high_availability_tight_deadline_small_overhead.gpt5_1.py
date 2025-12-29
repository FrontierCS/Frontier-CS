import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deluxe_cbl_mr_v1"

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

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Helper for NONE enum name differences
        NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))

        # Compute basic remaining quantities
        done = sum(self.task_done_time) if hasattr(self, "task_done_time") else 0.0
        remain_work = max(0.0, self.task_duration - done)
        remain_time = self.deadline - self.env.elapsed_seconds

        if remain_work <= 0.0:
            return NONE

        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds

        is_on_demand = last_cluster_type == ClusterType.ON_DEMAND
        is_spot = last_cluster_type == ClusterType.SPOT

        # Time needed if we commit to On-Demand starting now
        overhead_if_commit_now = self.remaining_restart_overhead if is_on_demand else restart_overhead

        # Safety: if we are at or past the point where we must run On-Demand to finish, do so.
        if remain_time <= remain_work + overhead_if_commit_now:
            return ClusterType.ON_DEMAND

        # If currently on On-Demand, optionally switch back to Spot only with ample slack
        if is_on_demand:
            if has_spot:
                # Require buffer for two restarts to be safe (switch to Spot now and possibly back later)
                if remain_time > remain_work + 2.0 * restart_overhead:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Not currently on On-Demand (either SPOT or NONE)
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: wait only if safe after waiting one step we can still finish on On-Demand
        if remain_time - gap >= remain_work + restart_overhead:
            return NONE

        # Otherwise, start On-Demand now to guarantee completion
        return ClusterType.ON_DEMAND