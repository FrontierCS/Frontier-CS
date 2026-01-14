import json
from argparse import Namespace
import math
from typing import List, Dict
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "my_strategy"  # REQUIRED: unique identifier
    
    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        
        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        
        # Load and analyze trace data
        self.trace_availability = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                # Read availability data (0/1 values)
                data = f.read().strip().split()
                availability = [int(x) for x in data]
                self.trace_availability.append(availability)
        
        self.num_regions = len(self.trace_availability)
        self.time_step = self.env.gap_seconds
        
        # Cost parameters
        self.spot_cost_per_sec = 0.9701 / 3600  # $/second
        self.ondemand_cost_per_sec = 3.06 / 3600  # $/second
        
        # Statistics tracking
        self.region_stats = [{"spot_available": 0, "total_steps": 0} 
                           for _ in range(self.num_regions)]
        self.current_step = 0
        
        return self
    
    def _calculate_risk_factor(self) -> float:
        """Calculate risk factor based on remaining time and work."""
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        # Adjust for pending overhead
        effective_work_left = work_left + self.remaining_restart_overhead
        
        time_left = self.deadline - self.env.elapsed_seconds
        
        if time_left <= 0:
            return float('inf')
        
        # Safety margin (10% of time left)
        safety_margin = 0.1 * time_left
        available_time = time_left - safety_margin
        
        if available_time <= 0:
            return float('inf')
        
        # Required work rate (work per second)
        required_rate = effective_work_left / available_time
        
        # Base work rate if using on-demand continuously
        base_rate = 1.0 / self.time_step  # Work per second if no interruptions
        
        return required_rate / base_rate
    
    def _find_best_spot_region(self) -> int:
        """Find region with highest spot availability probability."""
        best_region = self.env.get_current_region()
        best_score = -1
        
        current_step_index = int(self.env.elapsed_seconds // self.time_step)
        
        for region in range(self.num_regions):
            # Calculate recent availability in this region
            lookback = min(10, current_step_index)
            recent_available = 0
            
            for offset in range(1, lookback + 1):
                if current_step_index - offset >= 0:
                    recent_available += self.trace_availability[region][current_step_index - offset]
            
            if lookback > 0:
                recent_prob = recent_available / lookback
            else:
                recent_prob = 0
            
            # Look ahead a few steps (if available)
            lookahead = min(5, len(self.trace_availability[region]) - current_step_index - 1)
            future_available = 0
            
            for offset in range(1, lookahead + 1):
                future_available += self.trace_availability[region][current_step_index + offset]
            
            if lookahead > 0:
                future_prob = future_available / lookahead
            else:
                future_prob = 0
            
            # Combined score with more weight on recent history
            score = 0.6 * recent_prob + 0.4 * future_prob
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.current_step += 1
        
        # Calculate work progress
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        # If work is done, return NONE
        if work_left <= 0:
            return ClusterType.NONE
        
        # Calculate time remaining
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Emergency mode: if we're running out of time, use on-demand
        if time_left < work_left + self.restart_overhead + 2 * self.time_step:
            # Switch to best region first if needed
            best_region = self.env.get_current_region()
            for region in range(self.num_regions):
                if self.trace_availability[region][int(self.env.elapsed_seconds // self.time_step)]:
                    best_region = region
                    break
            
            if best_region != self.env.get_current_region():
                self.env.switch_region(best_region)
            
            # Use on-demand to ensure completion
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # Calculate risk factor
        risk_factor = self._calculate_risk_factor()
        
        # Update region statistics
        current_region = self.env.get_current_region()
        self.region_stats[current_region]["total_steps"] += 1
        if has_spot:
            self.region_stats[current_region]["spot_available"] += 1
        
        # If risk is high, use on-demand
        if risk_factor > 1.2:
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
        
        # If spot is available and risk is manageable, use spot
        if has_spot and risk_factor <= 1.2:
            # Check if we should switch regions for better spot reliability
            if last_cluster_type == ClusterType.SPOT:
                # Only consider switching if current region has poor recent availability
                recent_steps = min(5, self.region_stats[current_region]["total_steps"])
                if recent_steps > 0:
                    recent_availability = self.region_stats[current_region]["spot_available"] / recent_steps
                    if recent_availability < 0.5:
                        best_region = self._find_best_spot_region()
                        if best_region != current_region:
                            self.env.switch_region(best_region)
                            return ClusterType.SPOT
                
                return ClusterType.SPOT
            else:
                # Switching from non-spot to spot
                return ClusterType.SPOT
        
        # If spot not available but risk is low, try to switch to region with spot
        if not has_spot and risk_factor <= 1.0:
            best_region = self._find_best_spot_region()
            current_step_index = int(self.env.elapsed_seconds // self.time_step)
            
            # Check if best region has spot now
            if (best_region != current_region and 
                current_step_index < len(self.trace_availability[best_region]) and
                self.trace_availability[best_region][current_step_index]):
                
                self.env.switch_region(best_region)
                return ClusterType.SPOT
        
        # Default to on-demand if spot not available and we need to make progress
        if time_left < 3 * self.time_step or risk_factor > 0.8:
            return ClusterType.ON_DEMAND
        
        # Otherwise, pause to wait for better conditions
        return ClusterType.NONE