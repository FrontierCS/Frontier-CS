import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"

    def __init__(self, args):
        super().__init__()
        self.remaining_overhead = 0.0
        self.spot_available_history = []
        self.spot_availability_est = 0.5
        self.safety_factor = 1.2
        self.min_slack_hours = 4.0
        self.aggressiveness = 0.7

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update overhead timer
        if self.remaining_overhead > 0:
            self.remaining_overhead = max(0.0, self.remaining_overhead - self.env.gap_seconds)

        # Update spot availability estimate (exponential moving average)
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
        self.spot_availability_est = 0.95 * self.spot_availability_est + 0.05 * has_spot

        # Calculate progress and deadlines
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        current_slack = time_remaining - work_remaining

        # If work is complete, stop
        if work_remaining <= 0:
            return ClusterType.NONE

        # If we're in overhead period, wait
        if self.remaining_overhead > 0:
            return ClusterType.NONE

        # If we're critically behind, use on-demand immediately
        if current_slack < 0:
            return ClusterType.ON_DEMAND

        # Calculate effective required rate considering overheads
        if has_spot and self.spot_availability_est > 0:
            effective_spot_rate = self.spot_availability_est / (1 + self.restart_overhead * (1 - self.spot_availability_est) / self.env.gap_seconds)
        else:
            effective_spot_rate = 0.0

        # Dynamic threshold based on remaining time and work
        required_rate = work_remaining / time_remaining if time_remaining > 0 else float('inf')
        safe_threshold = required_rate * self.safety_factor

        # Use on-demand if spot cannot meet deadline with high probability
        if effective_spot_rate < required_rate:
            return ClusterType.ON_DEMAND

        # Conservative check: if slack is small, use on-demand
        if current_slack < self.min_slack_hours * 3600:
            return ClusterType.ON_DEMAND

        # Use spot when available and safe
        if has_spot:
            # Avoid restarting spot too often: check if we just had a preemption
            if last_cluster_type == ClusterType.SPOT or last_cluster_type == ClusterType.NONE:
                return ClusterType.SPOT
            # If switching to spot from on-demand, only do it if we have good slack
            if current_slack > 8 * 3600:  # 8 hours slack
                return ClusterType.SPOT

        # If spot unavailable but we have ample slack, wait
        if current_slack > max(12 * 3600, work_remaining * self.aggressiveness):
            return ClusterType.NONE

        # Otherwise use on-demand
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
