from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate progress and remaining work
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Calculate safety margin
        # We need to account for discrete time steps and potential overheads.
        # Margin ensures we switch to OD before it's strictly too late.
        # 3 * gap ensures we don't miss the deadline due to step granularity.
        # 300s adds a fixed safety buffer.
        margin = 3 * gap + 300

        # Calculate latest start time for On-Demand to guarantee completion.
        # We assume worst case: we must restart/incur overhead to run OD.
        # This provides a hysteresis effect: if we are on OD, we won't switch back
        # to Spot unless we have enough slack to absorb the overhead and still be safe.
        time_needed = remaining_work + overhead
        time_left = deadline - current_time

        # If we are close to the point of no return, force On-Demand
        if time_left <= time_needed + margin:
            return ClusterType.ON_DEMAND

        # Otherwise, try to use Spot to save cost
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable but we have slack, wait (pause)
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
