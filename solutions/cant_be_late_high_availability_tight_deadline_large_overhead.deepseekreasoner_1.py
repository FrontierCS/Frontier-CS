import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_spot_strategy"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize tracking variables
        self.spot_attempts = 0
        self.spot_failures = 0
        self.consecutive_spot_steps = 0
        self.last_decision = ClusterType.NONE
        self.spot_available_history = []
        self.work_remaining_history = []
        self.time_remaining_history = []
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track history for adaptive decisions
        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        
        # Calculate remaining work
        total_done = sum(self.task_done_time)
        work_remaining = self.task_duration - total_done
        time_remaining = deadline - current_time
        
        # Safety margin based on restart overhead
        safety_margin = self.restart_overhead * 2
        
        # Emergency mode: must finish soon
        if work_remaining > 0 and time_remaining <= work_remaining + safety_margin:
            return ClusterType.ON_DEMAND
        
        # Calculate efficiency metrics
        spot_efficiency = 0.7  # Conservative estimate
        if self.spot_failures > 0 and self.spot_attempts > 0:
            spot_efficiency = 1.0 - (self.spot_failures / self.spot_attempts)
            spot_efficiency = max(0.3, min(0.9, spot_efficiency))
        
        # Calculate time needed with different strategies
        time_needed_ondemand = work_remaining
        time_needed_spot = work_remaining / spot_efficiency if spot_efficiency > 0 else float('inf')
        
        # Can we finish with spot given current efficiency?
        spot_feasible = time_needed_spot <= time_remaining - safety_margin
        
        # Update spot availability history
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
        
        # Calculate spot availability probability
        spot_availability = 0.5  # Default
        if len(self.spot_available_history) > 10:
            available_count = sum(1 for avail in self.spot_available_history if avail)
            spot_availability = available_count / len(self.spot_available_history)
        
        # Adaptive strategy based on multiple factors
        use_spot = False
        use_ondemand = False
        
        # Factor 1: Time pressure
        time_pressure = max(0, 1 - (time_remaining / deadline))
        
        # Factor 2: Work progress
        work_progress = total_done / self.task_duration if self.task_duration > 0 else 0
        
        # Factor 3: Spot reliability
        spot_reliability = spot_availability * spot_efficiency
        
        # Decision logic
        if not has_spot:
            # Spot not available
            if time_pressure > 0.7 or not spot_feasible:
                use_ondemand = True
            else:
                # Wait for spot to become available if we have time
                wait_ok = time_remaining > work_remaining * 1.5 + safety_margin
                if wait_ok:
                    return ClusterType.NONE
                else:
                    use_ondemand = True
        else:
            # Spot is available
            if spot_reliability > 0.6 and spot_feasible:
                # Good conditions for spot
                if time_pressure < 0.8:
                    use_spot = True
                elif time_pressure < 0.9 and spot_reliability > 0.7:
                    use_spot = True
                else:
                    use_ondemand = True
            else:
                # Poor spot conditions
                if time_pressure < 0.5:
                    use_spot = True
                else:
                    use_ondemand = True
        
        # Update statistics
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_steps += 1
        else:
            self.consecutive_spot_steps = 0
        
        # Make final decision
        if use_spot:
            self.spot_attempts += 1
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT
        elif use_ondemand:
            if last_cluster_type == ClusterType.SPOT:
                self.spot_failures += 1
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        else:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
