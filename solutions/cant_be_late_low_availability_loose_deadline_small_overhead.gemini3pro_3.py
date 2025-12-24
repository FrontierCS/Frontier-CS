from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety Buffer Calculation:
        # We need to switch to reliable OD instances before it's too late.
        # We define a buffer to account for:
        # 1. The discrete decision steps (we commit for 'gap' seconds).
        # 2. A safety margin against potential timing issues or overhead loops.
        # Buffer = 2 steps + ~15 minutes (5 overheads) provides high safety with minimal cost impact given the 22h slack.
        buffer = (2.0 * gap) + (5.0 * overhead)
        
        # Critical threshold: The latest time we can comfortably finish using OD.
        # We include 'overhead' in the required time to cover the worst case (starting from stopped/spot).
        critical_threshold = work_remaining + overhead + buffer
        
        # 1. Panic Mode: If time is tight, force On-Demand to guarantee deadline
        if time_left < critical_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Cost Saving Mode: If we have slack, prefer Spot if available
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Wait Mode: If no Spot and plenty of time, pause to save money
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
