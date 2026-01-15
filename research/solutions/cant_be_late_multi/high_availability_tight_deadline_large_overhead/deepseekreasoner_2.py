import json
from argparse import Namespace
import math
from typing import List, Dict
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_scheduler"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.regions_data = []
        self.current_time = 0
        self.spot_schedule = {}
        self.region_count = 0
        self.time_slots = 0
        self.spot_availability = {}
        self.safety_margin = 1.5  # hours of safety margin

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

    def _parse_trace(self, trace_path: str) -> List[bool]:
        """Parse trace file to get spot availability."""
        availability = []
        try:
            with open(trace_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        availability.append(line.lower() == 'true')
        except:
            # If file doesn't exist or error, assume all true for initial strategy
            return [True] * 1000
        return availability

    def _initialize_strategy(self):
        """Initialize strategy data structures."""
        self.region_count = self.env.get_num_regions()
        self.time_slots = int(math.ceil(self.deadline / self.env.gap_seconds))
        
        # Initialize spot availability for all regions
        self.spot_availability = {}
        for region in range(self.region_count):
            # Note: Trace files are loaded by parent class
            # We'll query availability through has_spot parameter
            self.spot_availability[region] = [True] * self.time_slots

    def _get_remaining_work(self) -> float:
        """Get remaining work in seconds."""
        return self.task_duration - sum(self.task_done_time)

    def _get_time_left(self) -> float:
        """Get time left until deadline in seconds."""
        return self.deadline - self.env.elapsed_seconds

    def _should_use_ondemand(self) -> bool:
        """Determine if we should switch to on-demand based on time pressure."""
        remaining_work = self._get_remaining_work()
        time_left = self._get_time_left()
        
        # Convert to hours for easier calculation
        remaining_hours = remaining_work / 3600
        time_left_hours = time_left / 3600
        
        # If we're running out of time, use on-demand
        if time_left_hours < remaining_hours + self.safety_margin:
            return True
            
        # If overhead would cause us to miss deadline
        if time_left_hours < remaining_hours + self.restart_overhead / 3600:
            return True
            
        return False

    def _find_best_spot_region(self) -> int:
        """Find region with highest probability of spot availability."""
        current_region = self.env.get_current_region()
        best_region = current_region
        
        # Simple heuristic: try next region if current has no spot
        if not hasattr(self, 'last_spot_check'):
            self.last_spot_check = {}
            
        for i in range(self.region_count):
            region = (current_region + i) % self.region_count
            # Prefer regions we haven't recently checked
            if region not in self.last_spot_check or \
               self.current_time - self.last_spot_check[region] > 3600:  # 1 hour
                return region
                
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, 'initialized'):
            self._initialize_strategy()
            self.initialized = True
            
        self.current_time = self.env.elapsed_seconds
        
        # Update region spot check time
        current_region = self.env.get_current_region()
        self.last_spot_check[current_region] = self.current_time
        
        # Check if we're done
        if self._get_remaining_work() <= 0:
            return ClusterType.NONE
            
        # Check if we'll miss deadline
        time_left = self._get_time_left()
        if time_left <= 0:
            return ClusterType.NONE
            
        remaining_work = self._get_remaining_work()
        
        # If we're in restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Time pressure check - use on-demand if running out of time
        if self._should_use_ondemand():
            return ClusterType.ON_DEMAND
        
        # If spot is available, use it
        if has_spot:
            return ClusterType.SPOT
        else:
            # No spot in current region, try to find a better region
            best_region = self._find_best_spot_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, we need to check availability in next step
                return ClusterType.NONE
            else:
                # No better region found, use on-demand
                return ClusterType.ON_DEMAND