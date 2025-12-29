from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def __init__(self, args=None):
        super().__init__()

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Extract environment state
        elapsed_time = self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds if self.env.gap_seconds else 60.0
        
        # Calculate remaining work
        # self.task_done_time is a list of durations of completed segments
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is already done (or effectively done), do nothing
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        # Calculate time budget
        time_remaining = self.deadline - elapsed_time
        
        # Calculate the absolute minimum time required to finish using On-Demand.
        # We include restart_overhead because switching to OD or starting it 
        # usually incurs the overhead cost in time.
        min_required_time = work_remaining + self.restart_overhead
        
        # Safety margin configuration
        # We need a buffer to ensure we switch to OD before it becomes mathematically impossible
        # to finish. The buffer accounts for:
        # 1. Discrete time steps (we make decisions every gap_seconds)
        # 2. Potential simulation variance or floating point imprecision
        # A 15-minute (900s) static buffer plus 2 time steps is robust given the 22h slack.
        safety_buffer = 900.0 + (2.0 * gap_seconds)
        
        # Strategy Logic:
        # Check if we are approaching the "Point of No Return".
        # If remaining time is less than what's needed for OD plus safety,
        # we must switch to OD immediately to guarantee the deadline.
        if time_remaining < (min_required_time + safety_buffer):
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack, prefer Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we still have plenty of slack, 
        # wait (NONE) to avoid paying the high OD price.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)