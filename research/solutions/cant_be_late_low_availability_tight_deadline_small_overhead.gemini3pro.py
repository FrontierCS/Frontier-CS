from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Safety buffer in seconds (1 hour)
        # We maintain this much slack to handle future uncertainties and forced switches.
        SAFETY_BUFFER = 3600.0

        # Calculate work done (sum of completed segments) and remaining work
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Calculate time remaining until the hard deadline
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate current slack
        # Slack is the time cushion we have before we would miss the deadline 
        # assuming we ran perfectly on On-Demand from this moment.
        # Slack = Time_Available - Work_Needed
        current_slack = time_remaining - work_remaining

        # Strategy Logic:
        
        # 1. If Spot instances are unavailable:
        #    We must run On-Demand to guarantee progress. Waiting (NONE) consumes slack
        #    without progress, which is unacceptable given the high penalty for lateness
        #    and low Spot availability (4-40%).
        if not has_spot:
            return ClusterType.ON_DEMAND
        
        # 2. If Spot instances are available:
        
        #    a. If we are already running on Spot, continue doing so.
        #       It is the cheapest option and incurs no switching overhead.
        if last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT
            
        #    b. If we are not currently on Spot (either On-Demand or None),
        #       switching to Spot incurs a 'restart_overhead' penalty.
        #       We check if we can afford this penalty while maintaining our safety buffer.
        
        #       Calculate what the slack would be if we switched now (paying the overhead).
        effective_slack_after_switch = current_slack - self.restart_overhead
        
        if effective_slack_after_switch > SAFETY_BUFFER:
            # We have enough slack to absorb the switch cost and future risks.
            # Choose Spot to minimize cost.
            return ClusterType.SPOT
        else:
            # We are getting close to the deadline (low slack).
            # Do not risk paying the overhead to switch to Spot, or risk
            # future preemption overheads. Stick to (or switch to) On-Demand
            # to maximize the probability of meeting the deadline.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)