import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_urgency"

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
        
        # Initialize tracking variables
        self.region_history = []
        self.spot_availability = {}
        self.last_decision = None
        self.consecutive_no_spot = 0
        self.last_spot_region = None
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Update spot availability tracking
        self.spot_availability[current_region] = has_spot
        if has_spot:
            self.last_spot_region = current_region
            self.consecutive_no_spot = 0
        else:
            self.consecutive_no_spot += 1
        
        # Calculate remaining work and time
        total_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_work_done
        remaining_time = self.deadline - elapsed
        
        # If we're done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate urgency: how much work per time we need to maintain
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # Base success rate needed (work per step)
        base_required_per_step = remaining_work / (remaining_time / gap) if remaining_time > 0 else float('inf')
        
        # If we're in restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time, use on-demand
        emergency_threshold = 1.2 * base_required_per_step
        if required_rate > emergency_threshold and remaining_time < 4 * gap:
            return ClusterType.ON_DEMAND
        
        # High urgency: use on-demand if spot not available
        if required_rate > 1.1 * base_required_per_step and not has_spot:
            # Try to switch to a region with spot first
            best_region = self._find_best_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, we'll have restart overhead
                return ClusterType.NONE
            return ClusterType.ON_DEMAND
        
        # If spot is available and we're not in high urgency, use it
        if has_spot:
            # Check if we should switch to a better region
            if self.consecutive_no_spot > 2 and self.last_spot_region is not None:
                if self.last_spot_region != current_region:
                    self.env.switch_region(self.last_spot_region)
                    return ClusterType.NONE
            return ClusterType.SPOT
        
        # Spot not available, medium urgency
        if required_rate > 0.9 * base_required_per_step:
            # Try to find a region with spot
            best_region = self._find_best_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                return ClusterType.NONE
            # If no spot anywhere and we need to progress, use on-demand
            return ClusterType.ON_DEMAND
        
        # Low urgency: try to find spot in another region
        best_region = self._find_best_region()
        if best_region != current_region:
            self.env.switch_region(best_region)
            return ClusterType.NONE
        
        # If we can't find spot and not urgent, wait
        return ClusterType.NONE
    
    def _find_best_region(self) -> int:
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Check current region first
        if self.spot_availability.get(current_region, False):
            return current_region
        
        # Check other regions for spot availability
        for region in range(num_regions):
            if region != current_region and self.spot_availability.get(region, False):
                return region
        
        # If no spot anywhere, stay in current region
        return current_region