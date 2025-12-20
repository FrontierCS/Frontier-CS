from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        done_seconds = sum(self.task_done_time)
        remaining_work = self.task_duration - done_seconds

        if remaining_work <= 0:
            return ClusterType.NONE

        # Calculate remaining time until deadline
        time_left = self.deadline - self.env.elapsed_seconds

        # Calculate overhead if we were to switch to On-Demand now.
        # If we are already on On-Demand, there is no switch overhead.
        # If we are on Spot or None, we incur restart overhead.
        switch_overhead = 0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_overhead = self.restart_overhead

        # Safety buffer calculation
        # We include the restart overhead (x2 for safety) and a few time steps
        # to ensure we don't miss the deadline due to simulation granularity or floating point issues.
        buffer = (self.restart_overhead * 2.0) + (self.env.gap_seconds * 10.0)

        # Minimum time required to finish if we start On-Demand now
        time_needed_on_od = remaining_work + switch_overhead + buffer

        # Panic Condition: 
        # If remaining time is critically low, we must use On-Demand to guarantee completion.
        # This takes precedence over Spot availability.
        if time_left < time_needed_on_od:
            return ClusterType.ON_DEMAND

        # Cost Optimization:
        # If we have enough slack, we prefer Spot instances (cheaper).
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we still have slack, we choose NONE (Wait).
        # Waiting costs 0 money, whereas On-Demand is expensive.
        # We only switch to On-Demand when the Panic Condition triggers.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
