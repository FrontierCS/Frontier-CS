from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "JITScheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Calculate total work completed so far
        done_work = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - done_work

        # If work is essentially done, stop incurring costs
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time remaining until the hard deadline
        time_left = self.deadline - self.env.elapsed_seconds

        # Determine the "Panic Threshold"
        # This is the point of no return where we must switch to On-Demand to guarantee completion.
        # We need time equal to:
        # 1. Remaining Work
        # 2. Restart Overhead (in case we need to spin up a new OD instance)
        # 3. A small safety buffer (2 timesteps) to account for discrete step boundaries
        safety_buffer = self.restart_overhead + (2.0 * self.env.gap_seconds)
        panic_threshold = remaining_work + safety_buffer

        # Rule 1: Deadline Guarantee
        # If we are approaching the minimum time needed to finish on OD, force OD usage.
        # This avoids the -100,000 penalty.
        if time_left <= panic_threshold:
            return ClusterType.ON_DEMAND

        # Rule 2: Cost Minimization
        # If we have slack (time_left > panic_threshold), we prefer Spot.
        if has_spot:
            return ClusterType.SPOT

        # Rule 3: Wait for Savings
        # If Spot is unavailable but we still have slack, wait (NONE).
        # Burning OD early is wasteful since OD is guaranteed to be available later if needed.
        # We only burn OD when we hit the panic_threshold.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)