from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate the total work completed so far
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If work is finished, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE

        # Calculate the time remaining until the hard deadline
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Determine the overhead required if we switch to On-Demand right now.
        # If we are already running On-Demand, we assume no new overhead.
        # If we are on Spot or None, we must pay the restart overhead to start On-Demand.
        switch_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead

        # Add a safety buffer to handle the discrete time steps of the simulation.
        # If we cut it too close, we might miss the deadline by a fraction of a step.
        # 2.0 * gap_seconds ensures we switch with at least 2 steps of margin.
        safety_buffer = 2.0 * self.env.gap_seconds

        # Calculate the time required to finish using On-Demand
        required_time_od = remaining_work + switch_overhead + safety_buffer

        # Critical Check: Point of No Return
        # If the remaining time is close to the time required for On-Demand,
        # we MUST switch to On-Demand to guarantee completion.
        if remaining_time <= required_time_od:
            return ClusterType.ON_DEMAND

        # If we are not in the critical zone, minimize cost:
        # 1. Use Spot instances if available (cheapest option)
        # 2. If Spot is unavailable, wait (NONE) to save money, as we still have slack
        if has_spot:
            return ClusterType.SPOT
        
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
