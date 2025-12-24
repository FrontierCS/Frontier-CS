from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveDeadlineAwareStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        # If work is complete, do nothing (though environment should handle termination)
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = deadline - elapsed

        # --- Rule 1: Deadline Survival (Panic Mode) ---
        # Calculate the time strictly needed to finish if we commit to On-Demand immediately.
        # If we are not currently on On-Demand, we must pay the overhead to switch/start.
        switch_cost_to_od = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switch_cost_to_od = restart_overhead
            
        time_needed_od = work_rem + switch_cost_to_od
        
        # Safety Buffer:
        # We must ensure we can survive wasting this time step (gap) if we choose NOT to use OD.
        # If we choose NONE or SPOT (and fail), we lose 'gap' seconds.
        # We need to guarantee that at (t + gap), we are still solvable.
        # Using 1.1x gap provides a small margin for floating point / timing jitter.
        safety_buffer = 1.1 * gap + 0.01
        
        # If remaining time is critically low, force On-Demand usage.
        if time_rem <= time_needed_od + safety_buffer:
            return ClusterType.ON_DEMAND

        # --- Rule 2: Cost Optimization (Economy Mode) ---
        # If we are here, we have slack. We can try to save money.
        # Slack is the time buffer we have relative to the strict OD path.
        slack = time_rem - time_needed_od
        
        if has_spot:
            # Spot is available.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # We are on OD. Switching to Spot costs 'restart_overhead' (loss of progress).
                # Only switch if we have substantial slack to absorb this cost and future risks.
                # Threshold: 3x overhead allows for the switch cost + buffer for ~2 failures.
                if slack > 3.0 * restart_overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # We are on SPOT or NONE. Prefer Spot since it's cheaper and we have slack.
                return ClusterType.SPOT
        else:
            # Spot is unavailable.
            # Since we passed the panic check, we have enough slack to wait (NONE).
            # Waiting saves money compared to burning expensive OD time unnecessarily.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
