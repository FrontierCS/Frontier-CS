from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate the amount of work completed so far
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        
        # Calculate work remaining
        work_remaining = self.task_duration - work_done
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # Calculate time remaining until the hard deadline
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed

        # Determine restart overhead if we switch to On-Demand now.
        # We assume On-Demand is reliable (rate 1.0).
        # If we are already on On-Demand, no overhead. Otherwise, we pay overhead to switch/start.
        overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead = self.restart_overhead
        
        # Total time required to finish if we commit to On-Demand immediately
        time_needed_on_demand = work_remaining + overhead

        # Calculate Safety Buffer
        # We must ensure that if we choose NOT to use On-Demand in this step,
        # we still have enough time to finish using On-Demand starting from the NEXT step.
        # If we return NONE or SPOT, we consume 'gap_seconds' of time.
        # Condition for next step: (time_remaining - gap) >= time_needed_on_demand
        # Therefore, we need: time_remaining >= time_needed_on_demand + gap
        # We add a small multiplier (10%) and constant (5s) to the gap for robustness against floating point noise.
        gap = self.env.gap_seconds
        buffer = gap * 1.1 + 5.0

        # Panic Threshold Check
        # If time remaining is dangerously close to the minimum needed for On-Demand, force On-Demand.
        if time_remaining < (time_needed_on_demand + buffer):
            return ClusterType.ON_DEMAND

        # Strategy when we have slack:
        # 1. Prefer Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
        
        # 2. If Spot is unavailable but we have plenty of slack, wait (NONE).
        #    This avoids paying the high On-Demand price while waiting for Spot availability.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
