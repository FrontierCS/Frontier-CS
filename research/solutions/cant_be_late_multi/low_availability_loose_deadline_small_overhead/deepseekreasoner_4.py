import json
from argparse import Namespace
import math
import random
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with cost optimization."""
    
    NAME = "adaptive_multi_region"
    
    def __init__(self, args=None):
        """Initialize strategy."""
        super().__init__(args)
        self.region_data = []
        self.spot_prices = []
        self.on_demand_prices = []
        self.spot_available_history = []
        self.current_region = 0
        self.best_regions = []
        self.spot_availability_counts = []
        self.time_step = 0
        self.switch_penalty = 0
        self.risk_tolerance = 0.3
        self.consecutive_failures = 0
        
    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Initialize data structures
        num_regions = self.env.get_num_regions()
        self.region_data = [{
            'spot_available': True,
            'failures': 0,
            'successes': 0,
            'last_used': 0
        } for _ in range(num_regions)]
        
        # Price configuration
        spot_price_per_hour = 0.9701
        on_demand_price_per_hour = 3.06
        seconds_per_hour = 3600
        
        self.spot_prices = [spot_price_per_hour * self.env.gap_seconds / seconds_per_hour 
                           for _ in range(num_regions)]
        self.on_demand_prices = [on_demand_price_per_hour * self.env.gap_seconds / seconds_per_hour 
                                for _ in range(num_regions)]
        
        self.spot_available_history = [[] for _ in range(num_regions)]
        self.spot_availability_counts = [0 for _ in range(num_regions)]
        self.current_region = 0
        self.time_step = 0
        self.switch_penalty = self.restart_overhead[0] / self.env.gap_seconds
        self.risk_tolerance = 0.3  # Adjust based on remaining time
        
        return self
    
    def _calculate_time_pressure(self) -> float:
        """Calculate time pressure factor (0 to 1)."""
        elapsed = self.env.elapsed_seconds
        total_work = sum(self.task_done_time)
        work_remaining = self.task_duration[0] - total_work
        
        if work_remaining <= 0:
            return 0.0
        
        time_remaining = self.deadline - elapsed
        time_needed = work_remaining / self.env.gap_seconds
        
        # Account for restart overheads
        if self.remaining_restart_overhead > 0:
            time_needed += self.remaining_restart_overhead / self.env.gap_seconds
        
        # Return pressure factor (higher means more pressure)
        if time_remaining <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - (time_remaining / self.deadline) * 2))
    
    def _estimate_region_quality(self, region_idx: int, has_spot: bool) -> float:
        """Estimate quality score for a region (higher is better)."""
        if region_idx >= len(self.spot_availability_counts):
            return 0.0
        
        # Base score from historical availability
        hist_score = 0.0
        if self.spot_available_history[region_idx]:
            hist_score = sum(self.spot_available_history[region_idx]) / len(self.spot_available_history[region_idx])
        
        # Current availability bonus
        current_bonus = 2.0 if has_spot else 0.0
        
        # Distance penalty (prefer staying in current region)
        distance_penalty = 0.0
        if region_idx != self.current_region:
            distance_penalty = 0.1
            
        # Combine factors
        quality = hist_score * 0.7 + current_bonus * 0.3 - distance_penalty
        
        return quality
    
    def _select_best_region(self, has_spot: bool) -> int:
        """Select the best region to use."""
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Always check current region first
        best_region = current_region
        best_score = self._estimate_region_quality(current_region, has_spot)
        
        # Check other regions
        for region in range(num_regions):
            if region == current_region:
                continue
                
            # Simulate checking this region (we don't know actual has_spot for other regions)
            # Use historical data
            simulated_has_spot = False
            if self.spot_available_history[region]:
                # Assume similar pattern to history
                recent_availability = self.spot_available_history[region][-10:] if len(self.spot_available_history[region]) > 10 else self.spot_available_history[region]
                if recent_availability:
                    simulated_has_spot = sum(recent_availability) / len(recent_availability) > 0.5
            
            region_score = self._estimate_region_quality(region, simulated_has_spot)
            
            # Add bonus for regions with good historical performance
            if self.spot_availability_counts[region] > self.spot_availability_counts[best_region]:
                region_score *= 1.2
            
            if region_score > best_score * 1.1:  # 10% better to switch
                best_region = region
                best_score = region_score
        
        return best_region
    
    def _should_use_spot(self, has_spot: bool, time_pressure: float) -> bool:
        """Decide whether to use spot instances."""
        if not has_spot:
            return False
        
        # Calculate cost savings
        spot_cost = self.spot_prices[self.current_region]
        on_demand_cost = self.on_demand_prices[self.current_region]
        cost_saving = on_demand_cost - spot_cost
        
        # Adjust risk tolerance based on time pressure
        dynamic_risk = self.risk_tolerance * (1.0 - time_pressure)
        
        # Consider consecutive failures
        failure_penalty = self.consecutive_failures * 0.1
        
        # Use spot if risk-adjusted benefit is positive
        risk_adjusted_benefit = cost_saving * (1.0 - dynamic_risk) - failure_penalty
        
        return risk_adjusted_benefit > 0
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.time_step += 1
        
        # Update current region tracking
        self.current_region = self.env.get_current_region()
        
        # Update historical data
        self.spot_available_history[self.current_region].append(1 if has_spot else 0)
        if len(self.spot_available_history[self.current_region]) > 100:
            self.spot_available_history[self.current_region].pop(0)
        
        if has_spot:
            self.spot_availability_counts[self.current_region] += 1
        
        # Calculate progress and time pressure
        time_pressure = self._calculate_time_pressure()
        
        # If we have no time left, use on-demand
        if time_pressure > 0.95:
            return ClusterType.ON_DEMAND
        
        # Check if we're currently in overhead period
        if self.remaining_restart_overhead > 0:
            # During overhead, prefer to stay with current decision
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            elif last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Select best region
        best_region = self._select_best_region(has_spot)
        
        # Switch region if beneficial
        if best_region != self.current_region:
            self.env.switch_region(best_region)
            self.current_region = best_region
            # After switching, we need to restart
            # Use on-demand for stability after switch if time pressure is high
            if time_pressure > 0.5:
                self.consecutive_failures = 0
                return ClusterType.ON_DEMAND
        
        # Decide on instance type
        use_spot = self._should_use_spot(has_spot, time_pressure)
        
        if use_spot:
            self.consecutive_failures = 0
            return ClusterType.SPOT
        else:
            # If spot is not available or too risky, use on-demand
            if not has_spot:
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 0
            
            # Consider pausing if time pressure is low
            if time_pressure < 0.3 and not has_spot:
                # Small chance to wait for spot
                if random.random() < 0.1:
                    return ClusterType.NONE
            
            return ClusterType.ON_DEMAND