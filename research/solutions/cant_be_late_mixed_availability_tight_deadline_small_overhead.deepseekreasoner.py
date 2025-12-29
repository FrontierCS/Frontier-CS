import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.safety_buffer = None
        self.critical_time = None
        self.use_spot_aggressively = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate work done and remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds

        # Calculate effective time needed considering restart overhead
        if last_cluster_type == ClusterType.NONE:
            effective_time_needed = work_remaining + self.restart_overhead
        else:
            effective_time_needed = work_remaining

        # Determine safety buffer (conservative estimate)
        if self.safety_buffer is None:
            # Set safety buffer to 4x restart overhead initially
            self.safety_buffer = min(4 * self.restart_overhead, 3600)  # Cap at 1 hour
            self.use_spot_aggressively = True

        # Adjust strategy based on time pressure
        critical_threshold = effective_time_needed + self.safety_buffer
        is_critical = time_remaining <= critical_threshold

        # Dynamic safety buffer adjustment
        if not is_critical and time_remaining > 2 * critical_threshold:
            # Plenty of time, can be more aggressive with spot
            self.use_spot_aggressively = True
        elif is_critical:
            self.use_spot_aggressively = False

        # Strategy decision logic
        if is_critical:
            # Critical zone: use on-demand to guarantee completion
            return ClusterType.ON_DEMAND
        else:
            if has_spot and self.use_spot_aggressively:
                return ClusterType.SPOT
            elif has_spot and not self.use_spot_aggressively:
                # Moderate conservatism: use spot but be ready to switch
                if time_remaining > 1.5 * critical_threshold:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # No spot available, wait if we have time
                if time_remaining > 1.2 * critical_threshold:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)