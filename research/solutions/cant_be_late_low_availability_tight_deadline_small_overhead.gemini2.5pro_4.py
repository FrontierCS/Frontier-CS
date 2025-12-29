import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "dynamic_slack_strategy"

    def __init__(self, args):
        super().__init__(args)
        # Hyperparameter: Assumes an average spot instance lifetime of 2 hours,
        # which corresponds to 0.5 preemptions per hour of spot compute.
        self.exp_preemptions_per_hour = 0.5

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        try:
            work_done = sum(self.task_done_time)
        except (TypeError, IndexError):
            work_done = 0.0

        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # current_slack is the buffer we have if we run on-demand from now on.
        # A positive value means we are ahead of the on-demand-only schedule.
        current_slack = time_left - work_remaining

        # 1. Panic Mode:
        # If slack is non-positive, we are behind schedule even for a pure
        # on-demand strategy. We must use on-demand to have any chance of finishing.
        if current_slack <= 0:
            return ClusterType.ON_DEMAND

        # 2. Optimal Path:
        # If spot is available, it's always the most cost-effective choice for making
        # progress. The risk of preemption is managed by other logic branches.
        if has_spot:
            return ClusterType.SPOT

        # 3. No Spot Available - The Core Trade-off:
        # Decide whether to wait for spot (NONE) or pay for guaranteed progress (ON_DEMAND).
        # We maintain a dynamic "reserve" of slack to absorb future preemption overheads.
        # We only wait if our current slack exceeds this reserve.

        work_remaining_hours = work_remaining / 3600.0
        expected_future_preemptions = work_remaining_hours * self.exp_preemptions_per_hour
        
        dynamic_reserve_slack = expected_future_preemptions * self.restart_overhead

        if current_slack > dynamic_reserve_slack:
            # We have more slack than needed for our preemption buffer.
            # We can afford to spend this excess slack waiting for a cheap spot instance.
            return ClusterType.NONE
        else:
            # Our slack has dropped into the reserve buffer. We cannot afford
            # to wait any longer. Use on-demand to make progress while
            # preserving the remaining slack for potential future preemptions.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        REQUIRED: For evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)