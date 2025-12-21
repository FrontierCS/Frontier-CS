import json
from argparse import Namespace
from enum import Enum
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"
    
    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Precompute useful values
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.hourly_gap = self.env.gap_seconds / 3600.0  # hours per timestep
        
        # Initialize state
        self.last_region = 0
        self.consecutive_spot_failures = 0
        self.time_until_available = 0
        self.spot_history = []
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update state tracking
        current_region = self.env.get_current_region()
        if current_region != self.last_region:
            self.consecutive_spot_failures = 0
            self.last_region = current_region
        
        # Update spot availability history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 10:
            self.spot_history.pop(0)
        
        # Calculate progress and deadlines
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # If we're done, just pause
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate minimum time needed with various strategies
        min_ondemand_time = work_remaining  # Continuous on-demand
        min_spot_time_with_overhead = work_remaining + self.restart_overhead
        
        # Calculate safe thresholds
        emergency_threshold = min_ondemand_time * 1.1  # 10% buffer
        conservative_threshold = min_ondemand_time * 1.5
        
        # Emergency mode: must use on-demand to finish
        if time_remaining <= emergency_threshold:
            return self._emergency_strategy(has_spot)
        
        # Conservative mode: use on-demand if spot looks unreliable
        if time_remaining <= conservative_threshold:
            return self._conservative_strategy(has_spot, work_remaining, time_remaining)
        
        # Normal mode: optimize for cost
        return self._normal_strategy(has_spot, work_remaining, time_remaining)
    
    def _emergency_strategy(self, has_spot: bool) -> ClusterType:
        # In emergency, always use on-demand if available
        # But if we're switching from spot to on-demand in same region, that's okay
        return ClusterType.ON_DEMAND
    
    def _conservative_strategy(self, has_spot: bool, work_remaining: float, time_remaining: float) -> ClusterType:
        # Calculate if we can afford to try spot
        min_ondemand_time = work_remaining
        buffer_needed = time_remaining - min_ondemand_time
        
        # Try spot only if we have good buffer and spot is available
        if buffer_needed > self.restart_overhead * 2 and has_spot:
            # Check if spot seems reliable recently
            if self.spot_history.count(True) > self.spot_history.count(False) * 2:
                return ClusterType.SPOT
            elif self.consecutive_spot_failures < 2:
                return ClusterType.SPOT
        
        # Otherwise use on-demand
        return ClusterType.ON_DEMAND
    
    def _normal_strategy(self, has_spot: bool, work_remaining: float, time_remaining: float) -> ClusterType:
        current_region = self.env.get_current_region()
        
        # Calculate cost-effectiveness
        spot_cost_per_hour = self.spot_price
        ondemand_cost_per_hour = self.ondemand_price
        cost_ratio = ondemand_cost_per_hour / spot_cost_per_hour
        
        # Try to find better region if spot not available
        if not has_spot:
            best_region = self._find_best_region()
            if best_region is not None and best_region != current_region:
                self.env.switch_region(best_region)
                self.last_region = best_region
                self.consecutive_spot_failures = 0
                # After switching, we need to wait a step to know if spot is available
                # So return NONE for this timestep
                return ClusterType.NONE
        
        # If spot is available, use it most of the time
        if has_spot:
            # Calculate risk-adjusted value
            spot_success_rate = self._estimate_spot_reliability()
            expected_spot_cost = spot_cost_per_hour / spot_success_rate if spot_success_rate > 0 else float('inf')
            
            # Use spot if it's significantly cheaper considering reliability
            if expected_spot_cost < ondemand_cost_per_hour * 0.7:
                return ClusterType.SPOT
            # Or if we have plenty of time buffer
            elif work_remaining / time_remaining < 0.6:
                return ClusterType.SPOT
            else:
                # Mixed strategy: use spot 80% of time in normal mode
                import random
                if random.random() < 0.8:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        # If no spot available and we didn't switch region, use on-demand
        return ClusterType.ON_DEMAND
    
    def _find_best_region(self) -> int:
        """Find the region most likely to have spot available."""
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()
        
        # Simple round-robin search for next region
        # In a real implementation, we would track spot availability per region
        next_region = (current_region + 1) % num_regions
        return next_region
    
    def _estimate_spot_reliability(self) -> float:
        """Estimate spot reliability based on recent history."""
        if not self.spot_history:
            return 0.5  # Default guess
        
        true_count = self.spot_history.count(True)
        total = len(self.spot_history)
        
        # Weight recent history more heavily
        if total >= 3:
            recent_weight = 0.7
            older_weight = 0.3
            recent_count = self.spot_history[-3:].count(True)
            older_count = true_count - recent_count
            older_total = total - 3 if total > 3 else 0
            
            if older_total > 0:
                return (recent_count/3 * recent_weight + 
                       older_count/older_total * older_weight)
        
        return true_count / total if total > 0 else 0.5
