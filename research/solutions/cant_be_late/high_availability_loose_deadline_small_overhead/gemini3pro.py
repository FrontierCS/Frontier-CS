from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate"

    def __init__(self, args):
        self.args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment variables
        elapsed_seconds = self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds
        
        # Retrieve task configuration
        task_duration = self.task_duration
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_remaining = task_duration - work_done
        
        # If work is effectively completed, stop
        if work_remaining <= 1e-5:
            return ClusterType.NONE

        # --- Panic Logic ---
        # Calculate the absolute minimum time required to finish if we switch to On-Demand (OD) now.
        # We assume the worst case: switching incurs the full restart overhead.
        # Time needed = Work remaining + Restart overhead
        # If we wait one more step (gap_seconds) without making progress (e.g. paused or spot failed),
        # we lose 'gap_seconds' of slack.
        
        time_until_deadline = deadline - elapsed_seconds
        time_needed_for_od = work_remaining + restart_overhead
        
        # Calculate slack: Extra time available beyond what is needed for a safe OD run
        current_slack = time_until_deadline - time_needed_for_od
        
        # Safety Threshold:
        # If slack drops below this margin, we cannot afford to wait another step.
        # We use 1.5 * gap_seconds to buffer against floating point issues and discrete time steps.
        safety_threshold = 1.5 * gap_seconds
        
        if current_slack < safety_threshold:
            return ClusterType.ON_DEMAND
            
        # --- Cost Optimization Logic ---
        # If we are safe (plenty of slack):
        # 1. Use Spot if available (cheapest option).
        # 2. If Spot is unavailable, pause (NONE) to save money, rather than burning expensive OD.
        
        if has_spot:
            return ClusterType.SPOT
            
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)