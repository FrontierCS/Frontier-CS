from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

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
        remaining_work = self.get_remaining_task_duration()

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # Point of No Return (PNR) Check: If remaining time is less than
        # remaining work, we must use On-Demand to guarantee completion.
        # Add a one-step buffer for safety.
        if time_to_deadline <= remaining_work + self.env.gap_seconds:
            return ClusterType.ON_DEMAND

        # Opportunistic Spot: If spot is available and we are not in PNR,
        # always use it for cost savings.
        if has_spot:
            return ClusterType.SPOT

        # No Spot: Decide between On-Demand (guaranteed progress) or
        # NONE (wait for spot, save cost, but consume slack).
        slack = time_to_deadline - remaining_work

        # Use a dynamic safety buffer. We become more conservative (require more
        # slack) as the job progresses to mitigate risks near the deadline.
        progress = max(0.0, (self.task_duration - remaining_work) / self.task_duration)
        
        # Linearly scale the safety buffer multiplier with job progress.
        # These values are tuned heuristics.
        min_multiplier = 1.25
        max_multiplier = 2.25
        multiplier = min_multiplier + progress * (max_multiplier - min_multiplier)

        safety_buffer_threshold = self.restart_overhead * multiplier

        if slack <= safety_buffer_threshold:
            # Slack is too low, use On-Demand to avoid risk.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to wait for Spot instances to become available.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)
