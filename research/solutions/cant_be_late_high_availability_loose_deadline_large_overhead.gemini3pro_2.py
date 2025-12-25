from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "solution_strategy"

    def __init__(self, args):
        super().__init__()
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Gather environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        # Fallback to a reasonable default if gap is not provided (safety)
        if gap is None:
            gap = 300.0

        done_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_work)
        
        # If the task is effectively complete, do nothing
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_until_deadline = self.deadline - elapsed

        # Calculate the panic threshold
        # We must guarantee completion. The worst case is Spot becomes unavailable forever.
        # If we switch to OD, we incur restart_overhead.
        # We add a safety buffer (2 simulation steps) to account for discretization.
        safety_buffer = 2.0 * gap
        panic_threshold = remaining_work + self.restart_overhead + safety_buffer

        # If we are close to the deadline, force On-Demand usage to guarantee completion
        if time_until_deadline <= panic_threshold:
            return ClusterType.ON_DEMAND

        # If we have slack, prioritize Spot instances if available
        if has_spot:
            return ClusterType.SPOT

        # If we have slack but Spot is unavailable, wait (NONE) to save money
        # rather than burning budget on OD immediately
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)