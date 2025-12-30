from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_optimized_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        duration = self.task_duration
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        rem_work = max(0.0, duration - done)
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        time_left = deadline - elapsed
        
        # Buffer to ensure we don't miss deadline due to discrete steps or floating point
        BUFFER = 120.0

        if has_spot:
            # Spot is available. Default preference is SPOT to save cost.
            
            # Optimization: If we are currently on OD, switching to Spot incurs overhead.
            # We should only switch if we have enough slack to absorb the overhead and potential risks.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Calculate slack if we switch now (paying overhead)
                # We need rem_work + overhead time to finish
                slack_if_switch = time_left - (rem_work + overhead)
                
                # If switching puts us too close to the edge, stay on OD
                if slack_if_switch < BUFFER:
                    return ClusterType.ON_DEMAND
            
            # Otherwise, use Spot
            return ClusterType.SPOT
            
        else:
            # Spot unavailable. Choice is between ON_DEMAND (expensive) and NONE (wait).
            # We prefer to wait (NONE) to save money, as long as it's safe.
            
            # Calculate the slack if we wait for this time step.
            # If we wait:
            #   We lose 'gap' time.
            #   Our state becomes NONE (or stays NONE).
            #   To finish later, we will need to start OD, which costs 'overhead' + 'rem_work'.
            
            slack_after_wait = (time_left - gap) - (rem_work + overhead)
            
            if slack_after_wait < BUFFER:
                # Waiting is unsafe; we might miss the deadline. Must use OD.
                return ClusterType.ON_DEMAND
            else:
                # Safe to wait.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)