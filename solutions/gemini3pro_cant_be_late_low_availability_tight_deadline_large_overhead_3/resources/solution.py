from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CostOptimizedSafetyFirst"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current state
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        needed_work = self.task_duration - done_work
        
        # Check if work is already completed
        if needed_work <= 1e-6:
            return ClusterType.NONE

        deadline_time = self.deadline
        overhead = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Time remaining until deadline
        time_left = deadline_time - elapsed
        
        # Calculate Slack: Time we can afford to not work (wait or incur overhead)
        # S = T_rem - W_rem
        slack = time_left - needed_work
        
        # Safety margin to handle discrete timesteps and float precision
        safety_buffer = 2.0 * gap
        
        # Critical Threshold:
        # We must reserve enough slack to pay the 'overhead' cost to start an On-Demand instance.
        # If slack drops below this, we cannot guarantee finishing on time if we are not already running safely.
        critical_threshold = overhead + safety_buffer
        
        # 1. Critical Safety Check
        # If we are dangerously close to the deadline relative to work remaining, 
        # force On-Demand usage to guarantee completion.
        if slack < critical_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Strategy Logic
        if has_spot:
            # Case A: Continuing Spot
            # If we are already on Spot, we don't pay the entry overhead again.
            # We only need enough slack to handle the restart overhead if Spot gets preempted (switch to OD).
            if last_cluster_type == ClusterType.SPOT:
                if slack > critical_threshold:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            # Case B: Switching to Spot (from NONE or OD)
            # We incur entry overhead now, and risk incurring exit overhead later if Spot dies.
            # We need a reserve of 2 * overhead to safely attempt this transition.
            entry_threshold = 2.0 * overhead + safety_buffer
            
            if slack > entry_threshold:
                return ClusterType.SPOT
            else:
                # Not enough slack to risk the Spot entry+failure cost.
                # Running OD preserves our current slack buffer (safe).
                return ClusterType.ON_DEMAND
        else:
            # Case C: No Spot available
            # We have slack > critical_threshold (checked in step 1).
            # We can afford to wait (NONE) to save money, hoping Spot returns.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
