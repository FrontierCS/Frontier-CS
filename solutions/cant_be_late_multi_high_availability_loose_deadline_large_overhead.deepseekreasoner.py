import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "my_strategy"
    
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
        
        # Initialize strategy parameters
        self.danger_threshold = 0.3  # Start using on-demand when time ratio below this
        self.min_spot_confidence = 0.7  # Minimum confidence to use spot
        self.region_switch_penalty = 0.1  # Penalty for switching regions
        
        # Track region history
        self.region_history = []
        self.spot_availability_history = []
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()
        
        # If work is done, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we have pending overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_ratio = remaining_time / remaining_work if remaining_work > 0 else float('inf')
        
        # Update region history
        self.region_history.append(current_region)
        self.spot_availability_history.append(has_spot)
        
        # Calculate region stability (how long we've been in current region)
        region_stability = 1.0
        if len(self.region_history) > 1:
            recent_history = self.region_history[-min(10, len(self.region_history)):]
            region_stability = recent_history.count(current_region) / len(recent_history)
        
        # Calculate spot confidence for current region
        spot_confidence = 0.5  # Default confidence
        if len(self.spot_availability_history) > 0:
            recent_spot = self.spot_availability_history[-min(20, len(self.spot_availability_history)):]
            # Only consider times when we were in current region
            region_matches = [s for s, r in zip(recent_spot[-len(recent_spot):], 
                                               self.region_history[-len(recent_spot):]) 
                            if r == current_region]
            if region_matches:
                spot_confidence = sum(region_matches) / len(region_matches)
        
        # Emergency mode: very little time left
        if time_ratio < 1.2:
            # Use on-demand if we're running out of time
            return ClusterType.ON_DEMAND
        
        # Check if we should switch regions
        should_switch = False
        if not has_spot and spot_confidence < 0.3:
            # Current region has poor spot availability
            num_regions = self.env.get_num_regions()
            best_alternative = current_region
            best_score = -1
            
            # Evaluate other regions (simple round-robin)
            for i in range(num_regions):
                if i != current_region:
                    # Simple heuristic: try next region
                    if len(self.region_history) < 10 or i not in self.region_history[-10:]:
                        best_alternative = i
                        break
            
            if best_alternative != current_region:
                self.env.switch_region(best_alternative)
                should_switch = True
        
        # Decision logic
        if time_ratio < self.danger_threshold * 2:
            # Moderate time pressure - use on-demand
            return ClusterType.ON_DEMAND
        
        elif has_spot and spot_confidence > self.min_spot_confidence and region_stability > 0.5:
            # Good conditions for spot
            if time_ratio > self.danger_threshold * 3 or spot_confidence > 0.9:
                return ClusterType.SPOT
            else:
                # Mix of spot and on-demand based on confidence
                if spot_confidence > 0.8:
                    return ClusterType.SPOT
                else:
                    # Alternate between spot and on-demand
                    if len(self.region_history) % 4 < 3:
                        return ClusterType.SPOT
                    else:
                        return ClusterType.ON_DEMAND
        
        elif should_switch:
            # Just switched region, use on-demand for stability
            return ClusterType.ON_DEMAND
        
        elif has_spot:
            # Spot available but low confidence - use occasionally
            if len(self.region_history) % 3 == 0:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        else:
            # No spot available, use on-demand
            return ClusterType.ON_DEMAND
