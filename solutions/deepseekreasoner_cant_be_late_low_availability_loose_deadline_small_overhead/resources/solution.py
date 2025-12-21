import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.spec = None
        self.remaining_work = 0.0
        self.current_time = 0.0
        self.last_spot_available = False
        self.spot_availability_history = []
        self.spot_unavailable_duration = 0
        self.on_demand_used = 0.0
        self.spot_used = 0.0
        self.restart_pending = 0.0
        self.switch_to_od_time = None
        self.safety_margin_factor = 1.5

    def solve(self, spec_path: str) -> "Solution":
        self.spec = spec_path
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Update work tracking
        if last_cluster_type != ClusterType.NONE:
            work_done = min(gap, self.remaining_work)
            self.remaining_work = max(0, self.remaining_work - work_done)
        
        # Initialize remaining work if first call
        if current_time == 0:
            self.remaining_work = self.task_duration
        
        # Update availability tracking
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate availability metrics
        availability_rate = np.mean(self.spot_availability_history) if self.spot_availability_history else 0
        
        # Calculate time to deadline
        time_to_deadline = self.deadline - current_time
        
        # Calculate effective remaining time considering restart overhead
        if self.restart_pending > 0:
            effective_remaining_time = time_to_deadline - self.restart_pending
        else:
            effective_remaining_time = time_to_deadline
        
        # Base required rate to finish on time
        required_rate = self.remaining_work / max(1e-6, effective_remaining_time)
        
        # Conservative safety margin
        safety_margin = self.restart_overhead * self.safety_margin_factor
        
        # Decision logic
        if self.restart_pending > 0:
            # We're in restart overhead period
            self.restart_pending = max(0, self.restart_pending - gap)
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time, use on-demand
        if effective_remaining_time < self.remaining_work + safety_margin:
            if has_spot and availability_rate > 0.3 and self.remaining_work > self.restart_overhead * 2:
                # Still try spot if good availability and enough work to justify restart risk
                self.spot_used += gap
                return ClusterType.SPOT
            else:
                self.on_demand_used += gap
                return ClusterType.ON_DEMAND
        
        # Normal operation: use spot when available if we have time buffer
        if has_spot:
            # Check if we have enough buffer to risk spot
            time_buffer = effective_remaining_time - self.remaining_work
            if time_buffer > self.restart_overhead * 3 or availability_rate > 0.7:
                self.spot_used += gap
                return ClusterType.SPOT
        
        # If spot unavailable, decide between waiting or using on-demand
        if self.last_spot_available and not has_spot:
            # Spot just became unavailable, check if we should wait
            expected_wait_time = min(10 * gap, time_to_deadline * 0.1)
            if time_buffer > expected_wait_time + self.restart_overhead:
                return ClusterType.NONE
            elif availability_rate < 0.3:
                self.on_demand_used += gap
                return ClusterType.ON_DEMAND
        
        # Default to on-demand when spot is unavailable and we can't wait
        if not has_spot:
            self.on_demand_used += gap
            return ClusterType.ON_DEMAND
        
        self.last_spot_available = has_spot
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
