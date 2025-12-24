from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Calculate work state
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Get environment state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_remaining = deadline - elapsed
        overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # 3. Calculate panic threshold
        # We need a buffer to handle simulation step quantization and safety against deadline.
        # Buffer = Fixed margin (10 mins) + 2 timesteps
        # This ensures we switch to OD before it's mathematically impossible to finish.
        safety_buffer = 600 + (2 * gap)

        # Calculate time needed if we commit to On-Demand RIGHT NOW.
        # If we are currently on OD, we continue without overhead.
        # If we are on Spot or None, we incur overhead to switch/start OD.
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed_for_od = work_remaining
        else:
            time_needed_for_od = work_remaining + overhead

        # 4. Decision Logic
        
        # Panic Condition: If remaining time is close to minimum required time for OD, force OD.
        if time_remaining <= time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND

        # Standard Condition: If we have slack, prefer Spot to save cost.
        if has_spot:
            return ClusterType.SPOT

        # If Spot is unavailable and we have slack, pause to wait for Spot (save money).
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
