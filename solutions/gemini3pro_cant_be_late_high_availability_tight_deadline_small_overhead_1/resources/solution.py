from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "Solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # Current state
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        total_duration = self.task_duration
        overhead = self.restart_overhead
        
        # Calculate progress
        # task_done_time is a list of completed segment durations.
        progress = sum(self.task_done_time) if self.task_done_time else 0.0
        
        remaining_work = max(0.0, total_duration - progress)
        time_left = deadline - elapsed
        
        # Calculate Slack
        # Slack represents the amount of time we can afford to waste (waiting or restart overheads).
        # We subtract one overhead unit to ensure we always have time for at least one start/restart
        # operation without violating the deadline.
        slack = time_left - remaining_work - overhead
        
        # Strategy Thresholds (in seconds)
        # CRITICAL_SLACK: 1.2 hours.
        # If the buffer drops below this, we enter panic mode and use On-Demand
        # to guarantee the deadline is met. This protects against the severe penalty.
        CRITICAL_SLACK = 3600.0 * 1.2
        
        # WAIT_BUFFER: 2.5 hours.
        # If slack > WAIT_BUFFER, we have enough time to wait for Spot instances to become
        # available (ClusterType.NONE), saving money.
        # If slack <= WAIT_BUFFER, we stop waiting and use On-Demand to prevent the slack
        # from eroding further, "holding the line" to keep a safety margin for future Spot use.
        WAIT_BUFFER = 3600.0 * 2.5
        
        # Decision Logic
        
        # 1. Safety First: If we are close to the deadline relative to work left, use On-Demand.
        if slack < CRITICAL_SLACK:
            return ClusterType.ON_DEMAND
            
        # 2. Prefer Spot: If available and we are safe, use Spot (cheapest option).
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Handle Spot unavailability
        else:
            if slack > WAIT_BUFFER:
                # We have plenty of slack, wait for Spot to return.
                return ClusterType.NONE
            else:
                # Buffer is shrinking. Use On-Demand to maintain our safety margin.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
