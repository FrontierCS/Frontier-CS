from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_Solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current state parameters
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        remaining_work = task_duration - work_done
        
        # Check if job is finished
        if remaining_work <= 1e-7:
            return ClusterType.NONE
            
        time_left = deadline - elapsed
        
        # Determine the time cost to finish if we rely on On-Demand (OD) from now on.
        # If we are already on OD, we just need to finish the work.
        # If we are not on OD (Spot or None), we incur a restart overhead to switch/start OD.
        is_on_od = (last_cluster_type == ClusterType.ON_DEMAND)
        cost_to_finish_od = remaining_work + (0 if is_on_od else overhead)
        
        # Slack is the extra time we have available beyond the safe OD path.
        slack = time_left - cost_to_finish_od
        
        # Buffer ensures we don't bleed slack to zero.
        # If we choose NONE (wait), slack decreases by 'gap'. We must ensure slack > 0 for next step.
        buffer = gap * 1.5
        
        if has_spot:
            # Spot instances are available (cheaper).
            if is_on_od:
                # If currently on OD, switching to Spot costs 'overhead'.
                # We also risk Spot failing immediately, forcing a switch back to OD (another 'overhead').
                # We only switch if slack is large enough to absorb these costs.
                if slack > (2 * overhead + buffer):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            else:
                # If currently on Spot or None, and Spot is available, use it.
                # It is cheaper than OD and incurs the same immediate overhead as switching to OD (if coming from None).
                return ClusterType.SPOT
        else:
            # Spot not available.
            # If we have sufficient slack, wait (NONE) to save money.
            # If slack is critical, force OD to ensure deadline is met.
            if slack > buffer:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)