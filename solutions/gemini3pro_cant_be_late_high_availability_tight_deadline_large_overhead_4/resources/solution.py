from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate work done based on completed segments
        work_done = 0.0
        if self.task_done_time:
            for seg in self.task_done_time:
                work_done += (seg[1] - seg[0])

        remaining_work = self.task_duration - work_done
        
        # If finished, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        slack = time_left - remaining_work
        overhead = self.restart_overhead

        # Strategy Parameters
        # Total available slack is ~4 hours. Restart overhead is ~12 mins (0.2h).
        # We need to ensure we finish, so we default to On-Demand if slack gets low.
        
        # Threshold to bail from Spot to OD: ~1 hour of slack remaining (5 restarts).
        # This provides a safety buffer against the hard deadline penalty.
        SAFETY_THRESHOLD = overhead * 5.0
        
        # Threshold to switch from OD to Spot: ~1.6 hours of slack.
        # We require more slack to enter Spot to prevent thrashing and ensure stability.
        REJOIN_THRESHOLD = overhead * 8.0

        # If Spot is not available, we must use On-Demand to maximize utilization 
        # given the tight deadline (48h work in 52h window).
        if not has_spot:
            return ClusterType.ON_DEMAND

        # Spot is available
        if last_cluster_type == ClusterType.SPOT:
            # If we are already on Spot, stay on Spot unless slack is critical.
            # If slack is critically low, switch to OD to guarantee completion.
            # We check (slack > overhead * 1.5) to ensure we don't switch if paying the 
            # overhead would immediately cause us to fail or if we are already doomed.
            if slack < SAFETY_THRESHOLD and slack > overhead * 1.5:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT
            
        elif last_cluster_type == ClusterType.ON_DEMAND:
            # If we are on OD, only switch to Spot if we have a healthy slack buffer.
            # This saves money while keeping risk low.
            if slack > REJOIN_THRESHOLD:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
            
        else:
            # From NONE (start of job), prefer Spot.
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
