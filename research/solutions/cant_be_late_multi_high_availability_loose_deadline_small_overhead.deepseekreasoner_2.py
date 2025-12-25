import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with dynamic planning."""
    
    NAME = "dynamic_multi_region_planner"
    
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
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize state on first call
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._gap_seconds = self.env.gap_seconds
            self._num_regions = self.env.get_num_regions()
            self._current_region = self.env.get_current_region()
            self._spot_history = [[] for _ in range(self._num_regions)]
            self._region_switches = 0
            self._last_action = None
            self._consecutive_spot_failures = 0
            self._consecutive_on_demand = 0
            
        # Update current region
        self._current_region = self.env.get_current_region()
        
        # Update spot history
        self._spot_history[self._current_region].append(1 if has_spot else 0)
        # Keep only recent history (last 24 hours)
        max_history = int(24 * 3600 / self._gap_seconds)
        if len(self._spot_history[self._current_region]) > max_history:
            self._spot_history[self._current_region].pop(0)
        
        # Calculate critical metrics
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # Emergency mode if we're running out of time
        if remaining_time <= self.restart_overhead * 2 or remaining_work / remaining_time > 0.9:
            return self._emergency_mode(has_spot, remaining_work, remaining_time)
        
        # Calculate spot reliability for current region
        spot_reliability = self._calculate_spot_reliability(self._current_region)
        
        # Base decision logic
        decision = self._make_decision(
            last_cluster_type, 
            has_spot, 
            spot_reliability,
            remaining_work,
            remaining_time
        )
        
        # Track state for adaptive behavior
        self._last_action = decision
        if decision == ClusterType.SPOT:
            self._consecutive_on_demand = 0
        elif decision == ClusterType.ON_DEMAND:
            self._consecutive_on_demand += 1
            self._consecutive_spot_failures = 0
        
        return decision
    
    def _calculate_spot_reliability(self, region_idx: int) -> float:
        """Calculate spot reliability based on historical availability."""
        history = self._spot_history[region_idx]
        if not history:
            return 0.5  # Default if no history
        
        # Weight recent history more heavily
        weights = []
        total_weight = 0
        reliability = 0
        
        for i, available in enumerate(reversed(history)):
            weight = math.exp(-i / 10)  # Exponential decay
            weights.append(weight)
            total_weight += weight
            reliability += available * weight
        
        if total_weight > 0:
            reliability /= total_weight
        
        return reliability
    
    def _make_decision(self, last_cluster_type: ClusterType, has_spot: bool, 
                      spot_reliability: float, remaining_work: float, 
                      remaining_time: float) -> ClusterType:
        """Make the core scheduling decision."""
        
        # If we have pending restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_pressure = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # Always use on-demand if time pressure is high
        if time_pressure > 0.7:
            return ClusterType.ON_DEMAND
        
        # Consider switching regions if spot is unreliable here
        if (has_spot and spot_reliability < 0.3 and 
            self._consecutive_spot_failures < 3 and
            remaining_time > self.restart_overhead * 3):
            
            # Find best alternative region
            best_region, best_reliability = self._find_best_region()
            if (best_region != self._current_region and 
                best_reliability > spot_reliability + 0.2 and
                self._region_switches < 5):  # Limit region switches
                
                self.env.switch_region(best_region)
                self._region_switches += 1
                # After switching, we need to restart with overhead
                # Return NONE to let the restart happen
                return ClusterType.NONE
        
        # Main decision logic
        if not has_spot:
            if self._consecutive_spot_failures >= 2:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        # We have spot available
        if time_pressure > 0.5:
            # Moderate time pressure, mix spot and on-demand
            if self._consecutive_on_demand >= 2:
                # Give spot another chance after some on-demand
                return ClusterType.SPOT
            elif spot_reliability > 0.7:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # Low time pressure, prefer spot
            if spot_reliability > 0.6:
                return ClusterType.SPOT
            elif spot_reliability > 0.3 and self._consecutive_spot_failures == 0:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
    
    def _find_best_region(self) -> Tuple[int, float]:
        """Find the region with best spot reliability."""
        best_region = self._current_region
        best_reliability = self._calculate_spot_reliability(self._current_region)
        
        for region in range(self._num_regions):
            if region == self._current_region:
                continue
            reliability = self._calculate_spot_reliability(region)
            if reliability > best_reliability + 0.1:  # Significant improvement
                best_region = region
                best_reliability = reliability
        
        return best_region, best_reliability
    
    def _emergency_mode(self, has_spot: bool, remaining_work: float, 
                       remaining_time: float) -> ClusterType:
        """Emergency mode when running out of time."""
        # Calculate minimum required progress rate
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # If we can't make progress fast enough even with on-demand, use on-demand anyway
        if required_rate > 1.0 or remaining_time <= self.restart_overhead:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have some buffer, try spot
        if (has_spot and remaining_time > self.restart_overhead * 3 and
            self._consecutive_spot_failures == 0):
            return ClusterType.SPOT
        
        # Otherwise use on-demand
        return ClusterType.ON_DEMAND
