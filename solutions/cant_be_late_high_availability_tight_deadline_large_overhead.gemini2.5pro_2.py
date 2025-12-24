import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "slack_based_heuristic"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Set parameters from command-line arguments, with sane defaults
        k_cautious = getattr(self.args, 'k_cautious', 10.0)
        k_finish = getattr(self.args, 'k_finish', 1.0)

        # Pre-calculate thresholds based on the environment's restart_overhead
        self.panic_threshold = self.restart_overhead
        self.cautious_threshold = k_cautious * self.restart_overhead
        self.finish_threshold = k_finish * self.restart_overhead
        
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
        # Calculate current progress
        work_done = sum(end - start for start, end in self.task_done_time)

        # If the task is finished, do nothing to avoid extra costs
        if work_done >= self.task_duration:
            return ClusterType.NONE

        remaining_work = self.task_duration - work_done

        # Finishing rule: If very close to the end, use the reliable ON_DEMAND
        # instance to avoid a costly preemption for a small potential saving.
        if remaining_work <= self.finish_threshold:
            return ClusterType.ON_DEMAND

        # Calculate slack: the buffer of time we have before the deadline,
        # after accounting for the remaining work if done on a reliable instance.
        # This slack can be "spent" on waiting for spot or absorbing preemptions.
        current_time = self.env.elapsed_seconds
        slack = self.deadline - current_time - remaining_work

        # PANIC mode: If slack is less than what a single preemption would cost,
        # we cannot risk using a spot instance. We must use ON_DEMAND.
        if slack <= self.panic_threshold:
            return ClusterType.ON_DEMAND

        # If we have enough slack to survive at least one preemption:
        if has_spot:
            # Greedily use the cheap SPOT instance if it's available and safe.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide whether to wait or pay for ON_DEMAND.
            
            # COMFORTABLE mode: If slack is high, we can afford to wait.
            if slack > self.cautious_threshold:
                return ClusterType.NONE
            
            # CAUTIOUS mode: Slack is not critical, but not high. We preserve
            # it by using ON_DEMAND, rather than spending it by waiting.
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        parser.add_argument('--k_cautious', type=float, default=10.0)
        parser.add_argument('--k_finish', type=float, default=1.0)
        args, _ = parser.parse_known_args()
        return cls(args)
