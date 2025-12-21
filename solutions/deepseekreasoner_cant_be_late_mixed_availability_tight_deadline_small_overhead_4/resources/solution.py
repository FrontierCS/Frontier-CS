import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_threshold"

    def __init__(self, args):
        super().__init__(args)
        self.spot_history = []
        self.spot_availability_rate = 0.5  # Initial guess
        self.conservative_threshold = 0.7
        self.aggressive_threshold = 0.3
        self.switch_to_od_buffer = 0
        self.remaining_work = 0.0
        self.last_action = None
        self.od_only_time = 0.0
        self.switch_count = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _calculate_remaining_time(self, remaining_work: float) -> float:
        """Calculate remaining time needed considering restart overhead."""
        if self.last_action == ClusterType.NONE:
            return remaining_work
        # Estimate potential restart overheads
        estimated_restarts = max(0, (remaining_work / (self.env.gap_seconds * 10)) - 1)
        return remaining_work + estimated_restarts * self.restart_overhead

    def _should_switch_to_od(self, remaining_work: float, has_spot: bool) -> bool:
        """Determine if we should switch to on-demand."""
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        if time_remaining <= 0:
            return True
        
        # Calculate safe threshold
        time_needed = self._calculate_remaining_time(remaining_work)
        
        # If we're critically behind, switch to OD immediately
        if time_needed > time_remaining * 0.9:
            return True
        
        # If we have little slack time, be more conservative
        slack_ratio = time_remaining / max(1.0, time_needed)
        
        if slack_ratio < 1.5:  # Less than 50% slack
            threshold = self.conservative_threshold
        else:
            threshold = self.aggressive_threshold
        
        # Dynamic threshold based on spot availability
        if len(self.spot_history) > 10:
            recent_availability = sum(self.spot_history[-10:]) / 10.0
            if recent_availability < 0.3:
                threshold = 0.8  # Very conservative if spot is unreliable
            elif recent_availability > 0.7:
                threshold = max(0.2, threshold - 0.1)  # More aggressive
        
        # If spot is currently unavailable and we're above threshold, use OD
        if not has_spot and self.spot_availability_rate < threshold:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot history and availability rate
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        if self.spot_history:
            self.spot_availability_rate = sum(self.spot_history) / len(self.spot_history)
        
        # Calculate remaining work
        work_done = sum(end - start for start, end in self.task_done_time)
        self.remaining_work = max(0.0, self.task_duration - work_done)
        
        # Check if we're done
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Track last action for restart overhead estimation
        if last_cluster_type != self.last_action and last_cluster_type != ClusterType.NONE:
            self.switch_count += 1
        self.last_action = last_cluster_type
        
        # Emergency mode: if very close to deadline, use OD
        time_remaining = self.deadline - self.env.elapsed_seconds
        if time_remaining < 3600:  # Less than 1 hour remaining
            if has_spot and time_remaining > 1800:  # If >30 min, can try spot
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Determine if we should switch to OD
        if self._should_switch_to_od(self.remaining_work, has_spot):
            self.od_only_time = min(self.od_only_time + self.env.gap_seconds, 3600.0)
            return ClusterType.ON_DEMAND
        else:
            # Reset OD timer if using spot
            self.od_only_time = max(0.0, self.od_only_time - self.env.gap_seconds)
        
        # Use spot if available
        if has_spot:
            return ClusterType.SPOT
        
        # Spot not available - decide whether to wait or use OD
        time_needed = self._calculate_remaining_time(self.remaining_work)
        
        # If waiting would risk missing deadline, use OD
        if time_needed > time_remaining * 0.95:
            return ClusterType.ON_DEMAND
        
        # Otherwise wait for spot to become available
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
