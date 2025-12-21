import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"

    def solve(self, spec_path: str) -> "Solution":
        self.prices = {'spot': 0.97, 'ondemand': 3.06}
        self.prices_per_second = {
            ClusterType.SPOT: self.prices['spot'] / 3600,
            ClusterType.ON_DEMAND: self.prices['ondemand'] / 3600,
            ClusterType.NONE: 0.0
        }
        self.switch_to_od_threshold = 0.2
        self.spot_return_threshold = 0.4
        self.last_spot_unavailable_time = -float('inf')
        self.restart_count = 0
        self.consecutive_spot_steps = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - current_time
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.last_spot_unavailable_time = current_time
            self.restart_count += 1
        
        if has_spot and last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_steps += 1
        else:
            self.consecutive_spot_steps = 0
        
        time_needed_with_overhead = work_remaining + self.restart_overhead
        
        if time_remaining <= time_needed_with_overhead * 1.05:
            return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.SPOT and has_spot:
            if self.consecutive_spot_steps < 5:
                return ClusterType.SPOT
            else:
                reliability_score = min(self.consecutive_spot_steps * 0.05, 0.8)
                required_reliability = work_remaining / (time_remaining * 1.2)
                
                if reliability_score >= required_reliability:
                    return ClusterType.SPOT
                elif reliability_score >= required_reliability * 0.7:
                    return ClusterType.SPOT
                else:
                    if np.random.random() < 0.3:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.SPOT
        
        if has_spot:
            if last_cluster_type == ClusterType.NONE:
                time_since_unavailable = current_time - self.last_spot_unavailable_time
                if time_since_unavailable > 1800:
                    return ClusterType.SPOT
            
            urgency_factor = work_remaining / time_remaining
            spot_attempt_prob = 1.0 - min(urgency_factor * 1.5, 0.9)
            
            if np.random.random() < spot_attempt_prob:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND if urgency_factor > 0.4 else ClusterType.NONE
        else:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            
            urgency_factor = work_remaining / time_remaining
            
            if urgency_factor > self.switch_to_od_threshold:
                return ClusterType.ON_DEMAND
            else:
                wait_time = min(300, time_remaining - time_needed_with_overhead * 1.1)
                if wait_time > 60:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND if urgency_factor > 0.2 else ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
