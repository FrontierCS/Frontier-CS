from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "ThresholdStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Gather state
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        rem_work = self.task_duration - done_work
        
        # If task is effectively complete, do nothing
        if rem_work <= 1e-6:
            return ClusterType.NONE
            
        time_left = self.deadline - elapsed
        
        # Calculate logic thresholds
        # Safety buffer handles discrete time step granularity
        safety_buffer = self.env.gap_seconds * 2.0
        
        # The base time required to finish the work (excluding current overheads)
        base_time_needed = rem_work + safety_buffer
        
        # Threshold to START On-Demand (OD):
        # If we are not running (or need to switch), we incur restart_overhead.
        # If time_left drops to this point, we must start OD immediately to finish by deadline.
        start_threshold = base_time_needed + self.restart_overhead
        
        # Threshold to STOP On-Demand (OD):
        # If we are already running OD, we avoid stopping unless we have enough slack
        # to justify the cost of the restart overhead we will incur later.
        # We need: (Slack Time) > (Restart Overhead) to save money.
        # Stop if: time_left > start_threshold + restart_overhead
        stop_threshold = start_threshold + self.restart_overhead

        # Decision Logic
        if has_spot:
            # Spot is ~3x cheaper than OD. Always prefer if available.
            return ClusterType.SPOT
            
        # If Spot is unavailable:
        if last_cluster_type == ClusterType.ON_DEMAND:
            # We are currently running OD.
            # Only stop if we have substantial slack (hysteresis) to avoid flapping/paying overheads repeatedly.
            if time_left > stop_threshold:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        else:
            # We are currently NONE (waiting) or SPOT (just failed).
            # Only switch to expensive OD if we are close to the point of no return.
            if time_left <= start_threshold:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)