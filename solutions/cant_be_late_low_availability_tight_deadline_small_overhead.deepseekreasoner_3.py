import argparse
import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize state variables
        self._mode = "normal"  # normal, critical, or completed
        self._spot_unavailable_count = 0
        self._consecutive_on_demand = 0
        self._safety_buffer = 4 * 3600  # 4 hours initial buffer
        self._max_consecutive_spot = 100
        self._consecutive_spot = 0
        self._last_decision = ClusterType.NONE
        self._critical_threshold = 2 * 3600  # 2 hours until deadline
        
        # Read configuration if spec_path is provided
        # In this case, we use default parameters optimized for the environment
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # If work is already complete, do nothing
        if work_remaining <= 0:
            self._mode = "completed"
            return ClusterType.NONE
        
        # Check if we're in critical mode (approaching deadline)
        if time_remaining <= self._critical_threshold:
            self._mode = "critical"
        
        # Update counters
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._consecutive_on_demand += 1
            self._consecutive_spot = 0
        elif last_cluster_type == ClusterType.SPOT:
            self._consecutive_spot += 1
            self._consecutive_on_demand = 0
        else:
            self._consecutive_on_demand = 0
            self._consecutive_spot = 0
        
        if not has_spot:
            self._spot_unavailable_count += 1
        else:
            self._spot_unavailable_count = 0
        
        # Calculate required work rate to meet deadline
        if time_remaining <= 0:
            return ClusterType.NONE
        
        required_rate = work_remaining / time_remaining
        
        # Critical mode: use on-demand to ensure completion
        if self._mode == "critical":
            if required_rate > 0.8:  # Need high work rate
                return ClusterType.ON_DEMAND
            elif has_spot and required_rate <= 0.5:  # Can use spot if safe
                return ClusterType.SPOT
            elif not has_spot and required_rate <= 0.3:  # Can wait if safe
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        # Normal mode decision logic
        # Calculate safety margin considering restart overhead
        safety_margin = self.restart_overhead * 2  # Account for potential restart
        
        # Check if we can afford to use spot or wait
        can_afford_spot = (time_remaining - safety_margin) * self.env.gap_seconds >= work_remaining
        
        if not has_spot:
            # Spot unavailable - decide between on-demand and waiting
            if self._spot_unavailable_count < 5 and can_afford_spot:
                # Wait for spot to become available (short wait)
                return ClusterType.NONE
            else:
                # Use on-demand if waiting too long or critical
                if required_rate > 0.6 or not can_afford_spot:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.NONE
        
        # Spot is available
        if self._consecutive_on_demand > 10:
            # Been using on-demand too long, try to switch back to spot
            return ClusterType.SPOT
        
        if self._consecutive_spot > self._max_consecutive_spot:
            # Using spot for too long, use on-demand briefly to reset
            return ClusterType.ON_DEMAND
        
        # Use spot if we have enough time buffer
        if can_afford_spot:
            # Use spot with probability based on required rate
            # Higher required rate = higher probability of using on-demand
            spot_prob = max(0.1, 1.0 - required_rate * 1.5)
            
            if np.random.random() < spot_prob:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Not enough time buffer, use on-demand
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
