import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._init_state()

    def _init_state(self):
        self.last_decision = ClusterType.NONE
        self.in_overhead = False
        self.overhead_remaining = 0.0
        self.work_remaining = 0.0
        self.time_remaining = 0.0
        self.critical_time = 0.0
        self.consecutive_spot_attempts = 0
        self.spot_available_history = []
        self.window_size = 100

    def solve(self, spec_path: str) -> "Solution":
        # Reset state for new run
        self._init_state()
        return self

    def _update_state(self, last_cluster_type, has_spot):
        # Update work and time remaining
        self.work_remaining = self.task_duration - sum(self.task_done_time)
        self.time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Update overhead state
        if self.in_overhead:
            self.overhead_remaining = max(0, self.overhead_remaining - self.env.gap_seconds)
            if self.overhead_remaining <= 0:
                self.in_overhead = False
        
        # Track spot availability history
        self.spot_available_history.append(1 if has_spot else 0)
        if len(self.spot_available_history) > self.window_size:
            self.spot_available_history.pop(0)
        
        # Update consecutive spot attempts
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_attempts += 1
        else:
            self.consecutive_spot_attempts = 0

    def _should_use_on_demand(self):
        # Calculate how much work we could do with remaining time
        safe_work_time = self.time_remaining - self.restart_overhead
        
        # If we can't finish with any restarts, use on-demand
        if self.work_remaining > safe_work_time:
            return True
        
        # Calculate spot reliability from history
        if len(self.spot_available_history) >= 10:
            spot_reliability = sum(self.spot_available_history) / len(self.spot_available_history)
            
            # Estimate expected spot work given reliability
            expected_spot_work = spot_reliability * self.time_remaining
            
            # If expected spot work isn't enough, use on-demand
            if expected_spot_work < self.work_remaining:
                return True
        
        # If we've had many consecutive spot attempts without success
        if self.consecutive_spot_attempts > 5 and len(self.spot_available_history) > 0:
            recent_spot_availability = sum(self.spot_available_history[-5:]) / 5
            if recent_spot_availability < 0.3:
                return True
        
        return False

    def _get_spot_availability_score(self):
        if len(self.spot_available_history) < 5:
            return 0.5
        
        # Weight recent history more heavily
        recent_window = min(10, len(self.spot_available_history))
        recent_score = sum(self.spot_available_history[-recent_window:]) / recent_window
        
        # Use longer history for baseline
        long_window = min(50, len(self.spot_available_history))
        long_score = sum(self.spot_available_history[-long_window:]) / long_window if long_window > 0 else 0.5
        
        # Combine scores with more weight on recent
        return 0.7 * recent_score + 0.3 * long_score

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type, has_spot)
        
        # Check if we're in overhead period
        if self.in_overhead:
            return ClusterType.NONE
        
        # Safety check: always use on-demand if spot not available
        if not has_spot and self.work_remaining > 0:
            # Only switch to on-demand if we need to
            if self._should_use_on_demand():
                self.in_overhead = True
                self.overhead_remaining = self.restart_overhead
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # If work is done, do nothing
        if self.work_remaining <= 0:
            return ClusterType.NONE
        
        # Check if we should use on-demand
        if self._should_use_on_demand():
            self.in_overhead = True
            self.overhead_remaining = self.restart_overhead
            return ClusterType.ON_DEMAND
        
        # Calculate pressure factor (how close we are to deadline)
        pressure = 1.0 - (self.time_remaining / self.deadline)
        
        # Calculate spot score based on availability history
        spot_score = self._get_spot_availability_score()
        
        # Adjust spot usage based on pressure and spot reliability
        spot_threshold = 0.3 + (0.5 * (1.0 - pressure))
        
        # Calculate work rate needed
        needed_rate = self.work_remaining / self.time_remaining
        
        # Decide based on spot reliability and needed rate
        if has_spot and spot_score > spot_threshold and needed_rate > 0.3:
            self.in_overhead = True
            self.overhead_remaining = self.restart_overhead
            return ClusterType.SPOT
        
        # If spot is not reliable enough but we have time, wait
        if self.time_remaining > self.work_remaining * 1.5:
            return ClusterType.NONE
        
        # Otherwise use on-demand
        self.in_overhead = True
        self.overhead_remaining = self.restart_overhead
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
