import json
import math
from argparse import Namespace
from enum import IntEnum
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class NodeType(IntEnum):
    NONE = 0
    SPOT = 1
    ON_DEMAND = 2
    SWITCH = 3


class Solution(MultiRegionStrategy):
    NAME = "optimized_multi_region"

    def __init__(self, args):
        super().__init__(args)
        self.num_regions = None
        self.trace_data = None
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.deadline_steps = None
        self.task_steps = None
        self.overhead_steps = None
        self.gap_seconds = None
        self.dp = None
        self.best_path = None
        self.cost_dp = None

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

    def _load_traces(self) -> List[List[bool]]:
        """Load spot availability traces from files."""
        traces = []
        # We can't access trace_files from config in _step, so we'll load when needed
        # For now, return empty - actual loading would need access to config
        return traces

    def _seconds_to_steps(self, seconds: float) -> int:
        """Convert seconds to number of time steps."""
        if self.gap_seconds is None:
            self.gap_seconds = self.env.gap_seconds
        return math.ceil(seconds / self.gap_seconds)

    def _optimize_schedule(self) -> None:
        """Precompute optimal schedule using dynamic programming."""
        if self.num_regions is None:
            self.num_regions = self.env.get_num_regions()
        
        self.deadline_steps = self._seconds_to_steps(self.deadline)
        self.task_steps = self._seconds_to_steps(self.task_duration)
        self.overhead_steps = self._seconds_to_steps(self.restart_overhead)
        
        # Initialize DP tables
        max_steps = min(self.deadline_steps, self.task_steps + 10)
        self.dp = [[[float('inf')] * (self.num_regions) 
                   for _ in range(max_steps + 1)] 
                   for _ in range(self.task_steps + 1)]
        self.cost_dp = [[[float('inf')] * (self.num_regions) 
                        for _ in range(max_steps + 1)] 
                        for _ in range(self.task_steps + 1)]
        
        # Base case: 0 work done, at time 0, in any region
        for r in range(self.num_regions):
            self.dp[0][0][r] = 0
            self.cost_dp[0][0][r] = 0
        
        # Simulate transitions (we'll fill this with actual trace data if available)
        # For now, we'll use a heuristic approach in _step
        
        self.best_path = {}

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed_steps = self._seconds_to_steps(self.env.elapsed_seconds)
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        remaining_work = max(0, self.task_duration - work_done)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Check if we need to be conservative
        work_needed_steps = self._seconds_to_steps(remaining_work)
        time_left_steps = self._seconds_to_steps(remaining_time)
        
        # Calculate effective time per step considering overhead
        effective_time_per_step = self.gap_seconds
        if self.remaining_restart_overhead > 0:
            effective_time_per_step = max(0, self.gap_seconds - self.remaining_restart_overhead)
        
        # If we're very tight on time, use on-demand
        if time_left_steps <= work_needed_steps + 2:
            return ClusterType.ON_DEMAND
        
        # If we have plenty of time and spot is available, use spot
        if has_spot and time_left_steps > work_needed_steps * 1.5:
            # Check if we should switch regions for better reliability
            current_reliability = self._estimate_region_reliability(current_region)
            best_region, best_reliability = self._find_best_available_region()
            
            if (best_reliability > current_reliability * 1.2 and 
                self._should_switch_region(remaining_time, remaining_work)):
                self.env.switch_region(best_region)
                return ClusterType.SPOT
            
            return ClusterType.SPOT
        
        # If spot not available but we have time, wait or switch
        if not has_spot and time_left_steps > work_needed_steps * 2:
            # Try to find a region with spot
            for r in range(self.num_regions):
                if r != current_region:
                    # Switch to first available region
                    self.env.switch_region(r)
                    # We don't know if has_spot in new region yet, so use on-demand for safety
                    return ClusterType.ON_DEMAND
        
        # Default to on-demand for safety
        return ClusterType.ON_DEMAND
    
    def _estimate_region_reliability(self, region: int) -> float:
        """Estimate spot reliability for a region based on recent history."""
        # Simple heuristic: assume all regions are equally reliable
        # In a real implementation, we would track spot availability history
        return 0.8
    
    def _find_best_available_region(self) -> Tuple[int, float]:
        """Find the region with best estimated spot reliability."""
        best_region = self.env.get_current_region()
        best_score = 0.0
        
        for r in range(self.num_regions):
            score = self._estimate_region_reliability(r)
            if score > best_score:
                best_score = score
                best_region = r
        
        return best_region, best_score
    
    def _should_switch_region(self, remaining_time: float, remaining_work: float) -> bool:
        """Determine if it's worth switching regions."""
        # Only switch if we have enough time to absorb the overhead
        min_time_for_switch = remaining_work + self.restart_overhead * 2
        return remaining_time > min_time_for_switch
    
    def _calculate_required_rate(self, remaining_time: float, remaining_work: float) -> float:
        """Calculate the minimum work rate needed to finish on time."""
        if remaining_time <= 0:
            return float('inf')
        return remaining_work / remaining_time
    
    def _calculate_safe_rate(self) -> float:
        """Calculate a safe work rate that allows for some overhead."""
        total_time = self.deadline
        total_work = self.task_duration
        # Allow for 20% overhead time
        return total_work / (total_time * 0.8)
