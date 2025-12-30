from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate completed work and remaining work
        w_done = sum(self.task_done_time)
        w_rem = self.task_duration - w_done
        
        # If work is completed, stop
        if w_rem <= 0:
            return ClusterType.NONE

        # Time state
        t_curr = self.env.elapsed_seconds
        t_rem = self.deadline - t_curr
        
        # Calculate effective time required to finish on On-Demand
        # If we are not currently running On-Demand, we must factor in restart overhead
        # because switching to or starting On-Demand will incur this delay.
        time_needed_od = w_rem
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_od += self.restart_overhead
            
        # Slack is the time buffer we have available before we strictly MUST run OD
        slack = t_rem - time_needed_od
        
        # Define safety margin to switch to OD
        # We need to account for:
        # 1. The duration of the current step (gap_seconds) - we commit to this decision for this duration
        # 2. A buffer for at least one restart overhead (in case we try Spot and it fails immediately)
        # 3. Factor of 2.0 on gap ensures we don't run into negative slack during the step
        safety_margin = self.restart_overhead + 2.0 * self.env.gap_seconds
        
        # CRITICAL CONDITION: If slack is small, force On-Demand to guarantee deadline
        if slack < safety_margin:
            return ClusterType.ON_DEMAND
            
        # If we have slack, try to minimize cost
        if has_spot:
            # If we are currently on On-Demand, check if switching to Spot is safe/worth it.
            # Switching incurs overhead immediately (reducing slack).
            if last_cluster_type == ClusterType.ON_DEMAND:
                # We require a larger buffer to switch FROM safe OD TO risky Spot.
                # Threshold covers safety margin plus enough time to absorb the switch cost 
                # and potentially switch back if Spot fails.
                switch_threshold = safety_margin + 3.0 * self.restart_overhead
                
                if slack > switch_threshold:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            # If not on OD (i.e., NONE or SPOT), and Spot is available, use it.
            return ClusterType.SPOT
            
        # If Spot is not available and we have slack, wait (NONE) to save money.
        # We only run OD when slack < safety_margin.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)