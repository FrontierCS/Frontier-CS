import argparse
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
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_left_to_deadline = self.deadline - self.env.elapsed_seconds

        # This is the "Point of No Return" (PNR) check.
        # We calculate the worst-case time required to finish the job from this
        # point forward. The worst-case assumes we try to use a spot instance,
        # it gets immediately preempted, and we have to finish the rest of the
        # job on a reliable on-demand instance.
        # The total time required in this scenario is:
        # (the current time step duration) + (one restart overhead) + (all remaining work)
        worst_case_time_needed = (
            work_remaining + self.restart_overhead + self.env.gap_seconds
        )

        # If the time we have left until the deadline is not enough to cover this
        # worst-case scenario, we have no more safety buffer. We must switch to
        # the reliable on-demand instance to guarantee finishing on time.
        is_in_danger_zone = time_left_to_deadline <= worst_case_time_needed

        if is_in_danger_zone:
            return ClusterType.ON_DEMAND
        else:
            # If we have a safety buffer, we can afford to be cost-conscious.
            if has_spot:
                # Use the cheap spot instance if it's available.
                return ClusterType.SPOT
            else:
                # If spot is not available, we fall back to on-demand. This is a
                # conservative strategy. Instead of pausing (NONE) and "spending"
                # our valuable time buffer, we make progress on the task, thus
                # preserving the buffer for future spot unavailability or preemptions.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """REQUIRED: For evaluator instantiation"""
        args, _ = parser.parse_known_args()
        return cls(args)