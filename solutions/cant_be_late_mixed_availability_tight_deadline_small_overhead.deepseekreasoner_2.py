import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"

    def __init__(self, args):
        super().__init__(args)
        self.spec_config = {}
        self.spot_price = 0.97  # $/hr
        self.od_price = 3.06    # $/hr
        self.price_ratio = self.spot_price / self.od_price
        self.restart_penalty_hours = 0.05  # 3 minutes
        
    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress
        total_work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - total_work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # If work is done, stop all instances to minimize cost
        if work_remaining <= 0:
            return ClusterType.NONE
            
        # If we can't possibly finish even with 100% on-demand, use on-demand immediately
        if work_remaining > time_remaining:
            return ClusterType.ON_DEMAND
            
        # Calculate effective time considering restart overhead
        # We need to account for potential restarts if using spot
        effective_time_needed = work_remaining
        
        # If last step was spot and now spot is unavailable, we would incur restart overhead
        # But we don't know the future, so use a heuristic
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            # We just got preempted, so we need to add restart overhead
            effective_time_needed += self.restart_overhead
        
        # Calculate critical threshold: how much time we can "waste" on spot failures
        # before we must switch to on-demand to meet deadline
        time_slack = time_remaining - work_remaining
        
        # Adaptive threshold based on remaining time and work
        # More aggressive spot use early, more conservative as deadline approaches
        progress_ratio = total_work_done / self.task_duration
        time_ratio = self.env.elapsed_seconds / self.deadline
        
        # Calculate urgency factor (0 to 1, higher means more urgent)
        urgency = 1.0 - (time_remaining / (self.deadline * 0.5))
        urgency = max(0.0, min(1.0, urgency))
        
        # Calculate conservative factor based on work remaining vs time
        work_time_ratio = work_remaining / max(time_remaining, 0.001)
        conservative = min(1.0, work_time_ratio * 1.5)  # Be more conservative if ratio > 1
        
        # Combine factors
        spot_threshold = 0.5 * (1.0 - urgency) * (1.0 - conservative)
        
        # Always use on-demand if we're in the last hour or very close to deadline
        if time_remaining < 3600:  # Last hour
            return ClusterType.ON_DEMAND
            
        # Use on-demand if we're falling behind schedule
        expected_progress = self.env.elapsed_seconds / self.deadline
        if progress_ratio < expected_progress * 0.8:  # Behind schedule by 20%
            return ClusterType.ON_DEMAND
            
        # Use on-demand if spot availability is low and we're getting close
        if not has_spot and time_remaining < 7200:  # Last 2 hours
            return ClusterType.ON_DEMAND
            
        # Strategic decision making
        if has_spot:
            # If we just restarted or had a failure recently, be cautious
            recent_failures = 0
            if len(self.task_done_time) > 1:
                # Check if last interval was very short (potential failure)
                last_start, last_end = self.task_done_time[-1]
                if (last_end - last_start) < self.env.gap_seconds * 0.5:
                    recent_failures = 1
            
            # Calculate probability estimate for successful spot usage
            # Based on remaining time and restart overhead
            min_spot_time_needed = work_remaining / (1 + recent_failures * 0.5)
            spot_success_prob = min(1.0, time_slack / (self.restart_overhead * 2))
            
            # Use spot if probability is above threshold
            if spot_success_prob > spot_threshold:
                return ClusterType.SPOT
            else:
                # Fall back to on-demand if spot seems risky
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            # Use on-demand only if we must make progress now
            # Otherwise wait for spot to potentially save cost
            
            # Calculate how long we can afford to wait
            max_wait_time = time_remaining - work_remaining - self.restart_overhead
            
            if max_wait_time > 600:  # Can wait up to 10 minutes
                # Wait for spot to potentially come back
                return ClusterType.NONE
            else:
                # Need to make progress now
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
