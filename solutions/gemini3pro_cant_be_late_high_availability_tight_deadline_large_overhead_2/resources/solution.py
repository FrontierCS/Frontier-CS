from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "SlackHysteresisStrategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate progress
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # If work is complete, stop (save cost)
        if remaining_work <= 0:
            return ClusterType.NONE

        # Calculate time metrics
        time_remaining = self.deadline - self.env.elapsed_seconds
        slack = time_remaining - remaining_work
        
        # Determine threshold for switching from On-Demand to Spot
        # We need enough slack to absorb the restart overhead (lost time) + a safety buffer.
        # restart_overhead is typically 0.2h (720s).
        # We use 3x overhead: 1x consumed by the switch itself, 2x as remaining safety buffer.
        switch_threshold = self.restart_overhead * 3.0

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                # Already on cheap resource, stay there
                return ClusterType.SPOT
            
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # Currently on expensive resource. Spot is available.
                # Only switch if we have sufficient slack to risk the overhead.
                if slack > switch_threshold:
                    return ClusterType.SPOT
                else:
                    # Slack is tight, stick to reliability
                    return ClusterType.ON_DEMAND
            
            else:
                # Currently NONE (paused/starting), prefer Spot
                return ClusterType.SPOT
        else:
            # Spot unavailable.
            # Due to tight deadline (48h work in 52h window), we cannot afford to wait.
            # Must use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
