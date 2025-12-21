import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        time_per_step = self.env.gap_seconds
        restart_penalty = self.restart_overhead
        
        # Calculate critical threshold
        critical_time = remaining_work + restart_penalty
        buffer_needed = 2 * restart_penalty
        
        # Estimate spot reliability from recent history
        if hasattr(self, '_spot_history'):
            self._spot_history.append(has_spot)
            if len(self._spot_history) > 100:
                self._spot_history.pop(0)
            spot_reliability = sum(self._spot_history) / len(self._spot_history)
        else:
            self._spot_history = [has_spot]
            spot_reliability = 0.5
        
        # Dynamic threshold based on time pressure and spot reliability
        time_pressure = max(0, critical_time - time_left) / critical_time
        safety_margin = buffer_needed * (1.0 + time_pressure * 2.0)
        
        # Decide based on situation
        if time_left <= remaining_work:
            # Must use on-demand to guarantee completion
            return ClusterType.ON_DEMAND
        elif time_left <= remaining_work + safety_margin:
            # Critical zone - use on-demand if spot unreliable
            if has_spot and spot_reliability > 0.7:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Non-critical zone - use spot when available
            if has_spot:
                # Avoid frequent switching
                if (last_cluster_type == ClusterType.SPOT or 
                    last_cluster_type == ClusterType.NONE):
                    return ClusterType.SPOT
                else:
                    # Only switch back to spot if we have enough buffer
                    extra_buffer = time_left - (remaining_work + safety_margin)
                    if extra_buffer > restart_penalty * 3:
                        return ClusterType.SPOT
                    else:
                        return ClusterType.ON_DEMAND
            else:
                # Spot unavailable - decide between on-demand and waiting
                if time_left <= remaining_work + safety_margin * 1.5:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
