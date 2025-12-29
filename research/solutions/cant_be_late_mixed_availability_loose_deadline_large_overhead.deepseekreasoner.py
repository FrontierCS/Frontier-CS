import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold_solver"

    def __init__(self, args):
        super().__init__(args)
        self.initialized = False
        self.spot_price = 0.97  # per hour
        self.od_price = 3.06    # per hour
        self.time_step_hours = 0.0
        self.total_work_hours = 0.0
        self.deadline_hours = 0.0
        self.restart_hours = 0.0
        self.safety_factor = 1.2
        self.spot_history = []
        self.consecutive_spot_failures = 0
        self.last_decision = ClusterType.NONE
        self.remaining_work_hours = 0.0
        self.restart_timer = 0.0
        self.currently_in_restart = False

    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        # For this implementation, we'll use fixed parameters from problem description
        self.time_step_hours = 1.0 / 3600  # Assuming 1-second steps in hours
        self.total_work_hours = 48.0
        self.deadline_hours = 70.0
        self.restart_hours = 0.20
        self.remaining_work_hours = self.total_work_hours
        self.initialized = True
        return self

    def _calculate_work_remaining(self) -> float:
        """Calculate remaining work in hours"""
        if not self.task_done_time:
            return self.total_work_hours
        
        total_done = 0.0
        for start, end in self.task_done_time:
            total_done += (end - start) / 3600  # Convert seconds to hours
        
        remaining = max(0.0, self.total_work_hours - total_done)
        self.remaining_work_hours = remaining
        return remaining

    def _calculate_time_remaining(self) -> float:
        """Calculate time remaining until deadline in hours"""
        elapsed_hours = self.env.elapsed_seconds / 3600
        return max(0.0, self.deadline_hours - elapsed_hours)

    def _calculate_required_od_time(self, work_remaining: float) -> float:
        """Calculate minimum on-demand time needed to finish work"""
        return work_remaining

    def _calculate_required_spot_time(self, work_remaining: float) -> float:
        """Calculate expected spot time needed including restart overhead"""
        # Assuming 30% spot availability on average
        avg_availability = 0.3
        effective_rate = avg_availability * (1 - 0.1)  # 10% time lost to restarts
        if effective_rate > 0:
            return work_remaining / effective_rate
        return float('inf')

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            return ClusterType.ON_DEMAND
        
        # Update restart timer
        if self.currently_in_restart:
            self.restart_timer -= self.time_step_hours
            if self.restart_timer <= 0:
                self.currently_in_restart = False
        
        # Calculate current state
        work_remaining = self._calculate_work_remaining()
        time_remaining = self._calculate_time_remaining()
        elapsed_hours = self.env.elapsed_seconds / 3600
        
        # If no work left, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If we're in restart overhead, wait
        if self.currently_in_restart:
            return ClusterType.NONE
        
        # Calculate critical threshold
        required_od_time = self._calculate_required_od_time(work_remaining)
        buffer_needed = self.restart_hours * 2  # Safety buffer for restarts
        
        # Emergency mode: must use on-demand to meet deadline
        if time_remaining <= required_od_time * self.safety_factor:
            # Start restart overhead if switching from spot
            if last_cluster_type == ClusterType.SPOT:
                self.currently_in_restart = True
                self.restart_timer = self.restart_hours
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # Try to use spot when available
        if has_spot:
            # Calculate if we have enough time for spot
            expected_spot_time = self._calculate_required_spot_time(work_remaining)
            time_for_spot = time_remaining - buffer_needed
            
            if expected_spot_time <= time_for_spot:
                # Start restart overhead if switching from non-spot
                if last_cluster_type != ClusterType.SPOT and last_cluster_type != ClusterType.NONE:
                    self.currently_in_restart = True
                    self.restart_timer = self.restart_hours
                    return ClusterType.NONE
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            else:
                # Not enough time for spot, use on-demand
                if last_cluster_type == ClusterType.SPOT:
                    self.currently_in_restart = True
                    self.restart_timer = self.restart_hours
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            self.consecutive_spot_failures += 1
            
            # If we've had many spot failures, be more aggressive with on-demand
            if self.consecutive_spot_failures > 10:
                if last_cluster_type == ClusterType.SPOT:
                    self.currently_in_restart = True
                    self.restart_timer = self.restart_hours
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND
            
            # Check if we should wait for spot or use on-demand
            time_needed_with_od = required_od_time * 1.1  # 10% buffer
            
            if time_remaining > time_needed_with_od * 1.5:
                # We have time to wait for spot
                return ClusterType.NONE
            else:
                # Getting tight, use on-demand
                if last_cluster_type == ClusterType.SPOT:
                    self.currently_in_restart = True
                    self.restart_timer = self.restart_hours
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)