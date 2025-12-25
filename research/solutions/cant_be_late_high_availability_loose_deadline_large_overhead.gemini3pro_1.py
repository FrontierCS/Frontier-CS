from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "TargetSlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # Calculate slack: the extra time we have available beyond what is strictly 
        # needed to finish using On-Demand (the safe baseline).
        # If we are not currently running On-Demand, we must account for the overhead 
        # time to switch/start an instance.
        switch_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_cost = overhead
            
        time_needed_od = remaining_work + switch_cost
        slack = time_left - time_needed_od

        # Thresholds
        # 1. Critical Buffer: Account for discrete time steps and small delays.
        #    If slack is below this, we are in danger of missing the deadline.
        CRITICAL_BUFFER = max(900, 3 * self.env.gap_seconds)
        
        # 2. Safe Buffer: Reserve a block of slack (4 hours) to handle future uncertainties.
        #    While slack > SAFE_BUFFER, we can afford to wait for Spot or risk interruptions.
        #    When slack < SAFE_BUFFER, we prioritize finishing the task over cost savings.
        SAFE_BUFFER = 4 * 3600

        # Decision Logic
        if slack < CRITICAL_BUFFER:
            return ClusterType.ON_DEMAND
            
        if slack < SAFE_BUFFER:
            # Conservative Mode:
            # We are getting close to the deadline.
            # If we are already comfortably running on Spot, keep doing so (cheapest path).
            # However, if we are interrupted or not on Spot, do not risk the startup overhead 
            # or waiting time for Spot. Switch to On-Demand to guarantee completion.
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
            
        # Aggressive Mode (High Slack):
        # We have plenty of time. Prioritize using Spot instances.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable, wait (return NONE) to save money.
        # We can afford to burn slack here because we have a large buffer.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)