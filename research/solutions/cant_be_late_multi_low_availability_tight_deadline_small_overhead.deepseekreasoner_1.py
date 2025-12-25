import json
from argparse import Namespace
import math
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "multi_region_optimizer"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701  # $/hour
        self.ondemand_price = 3.06  # $/hour
        self.price_ratio = self.ondemand_price / self.spot_price
        
        # Strategy parameters (tuned for the evaluation environment)
        self.min_spot_confidence = 0.6
        self.emergency_threshold = 0.25
        self.switch_threshold = 0.15
        
        # Will be initialized in solve()
        self.trace_data = []
        self.region_availability = []
        self.current_region_history = []
        self.spot_availability_window = 10
        
        # Cached computations
        self._remaining_work_cache = None
        self._time_left_cache = None

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
        
        # Load trace data if available
        if "trace_files" in config:
            self.trace_data = []
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file, 'r') as f:
                        # Simple trace parsing - adjust based on actual format
                        lines = f.readlines()
                        availability = [1 if '1' in line or 'available' in line.lower() else 0 
                                      for line in lines if line.strip()]
                        self.trace_data.append(availability)
                except:
                    self.trace_data.append([])
            
            # Initialize region availability stats
            self.region_availability = []
            for trace in self.trace_data:
                if trace:
                    available_count = sum(trace)
                    total_count = len(trace)
                    self.region_availability.append(available_count / max(total_count, 1))
                else:
                    self.region_availability.append(0.0)
        
        self.current_region_history = []
        return self

    def _get_remaining_work(self) -> float:
        """Get remaining work in seconds."""
        if self._remaining_work_cache is None:
            completed = sum(self.task_done_time) if self.task_done_time else 0
            self._remaining_work_cache = max(0, self.task_duration - completed)
        return self._remaining_work_cache

    def _get_time_left(self) -> float:
        """Get time left until deadline in seconds."""
        if self._time_left_cache is None:
            self._time_left_cache = max(0, self.deadline - self.env.elapsed_seconds)
        return self._time_left_cache

    def _clear_caches(self):
        """Clear cached computations."""
        self._remaining_work_cache = None
        self._time_left_cache = None

    def _get_best_alternative_region(self, current_region: int, has_spot: bool) -> Tuple[int, bool]:
        """Find the best alternative region with spot availability."""
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_has_spot = has_spot
        
        if len(self.trace_data) >= num_regions:
            current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
            
            # Look ahead in current region
            if has_spot and current_region < len(self.trace_data):
                trace = self.trace_data[current_region]
                future_available = 0
                lookahead = min(self.spot_availability_window, len(trace) - current_step - 1)
                for i in range(1, lookahead + 1):
                    if current_step + i < len(trace) and trace[current_step + i]:
                        future_available += 1
                current_confidence = future_available / lookahead if lookahead > 0 else 0
            
            # Check other regions
            for region in range(num_regions):
                if region == current_region:
                    continue
                    
                if region < len(self.trace_data):
                    trace = self.trace_data[region]
                    if current_step < len(trace) and trace[current_step]:
                        # Check future availability in this region
                        future_available = 0
                        lookahead = min(self.spot_availability_window, len(trace) - current_step - 1)
                        for i in range(1, lookahead + 1):
                            if current_step + i < len(trace) and trace[current_step + i]:
                                future_available += 1
                        region_confidence = future_available / lookahead if lookahead > 0 else 0
                        
                        # Consider switching if better than current
                        if region_confidence > self.min_spot_confidence:
                            return region, True
        
        return best_region, best_has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Clear caches at start of each step
        self._clear_caches()
        
        current_region = self.env.get_current_region()
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_left()
        
        # Update history
        self.current_region_history.append(current_region)
        if len(self.current_region_history) > 20:
            self.current_region_history.pop(0)
        
        # Emergency mode: if we're running out of time, use on-demand
        if remaining_work > 0:
            work_time_needed = remaining_work
            if last_cluster_type != ClusterType.NONE and self.remaining_restart_overhead > 0:
                work_time_needed += self.restart_overhead
            
            # Calculate safety margin
            safety_margin = self.restart_overhead * 2
            if work_time_needed + safety_margin > time_left * self.emergency_threshold:
                # Emergency - must use on-demand to guarantee completion
                return ClusterType.ON_DEMAND
        
        # If no spot available in current region, consider switching
        if not has_spot and last_cluster_type != ClusterType.ON_DEMAND:
            # Check if we should switch to another region with spot
            new_region, new_has_spot = self._get_best_alternative_region(current_region, has_spot)
            if new_region != current_region and new_has_spot:
                # Only switch if we've been in current region for a while
                if len(self.current_region_history) >= 3:
                    recent_regions = set(self.current_region_history[-3:])
                    if len(recent_regions) == 1:  # Been in same region
                        self.env.switch_region(new_region)
                        return ClusterType.SPOT
            
            # No good alternative region with spot, use on-demand
            return ClusterType.ON_DEMAND
        
        # If we have spot available and it's reliable, use it
        if has_spot:
            # Calculate confidence in current region
            confidence = 1.0
            if current_region < len(self.region_availability):
                confidence = self.region_availability[current_region]
            
            if confidence >= self.min_spot_confidence:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.SPOT:
                # Continue with spot if we're already on it
                return ClusterType.SPOT
        
        # Default to on-demand if spot is not reliable
        return ClusterType.ON_DEMAND
