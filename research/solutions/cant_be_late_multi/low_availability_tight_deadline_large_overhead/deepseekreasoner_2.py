import json
from argparse import Namespace
from typing import List, Tuple
import math
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "efficient_multi_region"

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

        # Pre-calculate constants
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        self.critical_slack_ratio = 0.3  # Use on-demand when slack < 30% of remaining work
        self.switch_penalty_ratio = 0.1  # Switch region if spot availability difference > 10%
        
        # Initialize region tracking
        self.region_spot_history = []
        self.region_stats = []
        self.current_region = 0
        self.consecutive_none = 0
        self.max_consecutive_none = 3
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate remaining work and slack
        work_done = sum(self.task_done_time)
        remaining_work = max(0, self.task_duration - work_done)
        deadline = self.deadline
        time_left = deadline - elapsed
        
        # Emergency mode: must finish
        if time_left <= remaining_work + self.restart_overhead:
            # Use on-demand if no overhead pending
            if self.remaining_restart_overhead <= 0:
                return ClusterType.ON_DEMAND
            # Otherwise wait for overhead to finish
            return ClusterType.NONE
        
        # Calculate safe slack ratio
        if remaining_work > 0:
            slack_ratio = (time_left - remaining_work) / remaining_work
        else:
            slack_ratio = float('inf')
        
        # Update region statistics
        if len(self.region_spot_history) <= current_region:
            self.region_spot_history.append([])
            self.region_stats.append({'available': 0, 'total': 0})
        
        self.region_stats[current_region]['total'] += 1
        if has_spot:
            self.region_stats[current_region]['available'] += 1
        
        # Strategy decision
        # 1. Check if we should switch regions
        if self._should_switch_region(current_region, num_regions, has_spot):
            best_region = self._find_best_spot_region(current_region, num_regions)
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, wait for restart overhead if any
                if self.remaining_restart_overhead > 0:
                    return ClusterType.NONE
        
        # 2. Check restart overhead
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # 3. Determine cluster type based on risk assessment
        if slack_ratio < self.critical_slack_ratio:
            # Low slack, use on-demand for reliability
            return ClusterType.ON_DEMAND
        
        # 4. Use spot if available and we're not in a critical situation
        if has_spot:
            # Reset consecutive none counter when we get spot
            self.consecutive_none = 0
            
            # Only use spot if we have enough buffer for potential restart
            buffer_needed = remaining_work * 1.2  # 20% buffer
            if time_left > buffer_needed + self.restart_overhead:
                return ClusterType.SPOT
            else:
                # Too risky, use on-demand
                return ClusterType.ON_DEMAND
        
        # 5. No spot available
        self.consecutive_none += 1
        
        # If we've been waiting too long, consider on-demand
        if (self.consecutive_none > self.max_consecutive_none and 
            slack_ratio < 0.5):  # Moderate slack
            return ClusterType.ON_DEMAND
        
        # Otherwise wait for spot
        return ClusterType.NONE
    
    def _should_switch_region(self, current_region: int, num_regions: int, has_spot: bool) -> bool:
        """Determine if we should switch to another region."""
        if num_regions <= 1:
            return False
        
        # Don't switch if we're in the middle of work
        if self.remaining_restart_overhead > 0:
            return False
        
        # If current region has no spot and we can switch
        if not has_spot and self.consecutive_none >= 2:
            return True
        
        # Check if another region has significantly better spot availability
        current_availability = self._get_region_availability(current_region)
        if current_availability < 0.5:  # Less than 50% availability
            return True
        
        return False
    
    def _get_region_availability(self, region_idx: int) -> float:
        """Get spot availability for a region."""
        if region_idx >= len(self.region_stats):
            return 0.0
        stats = self.region_stats[region_idx]
        if stats['total'] == 0:
            return 0.0
        return stats['available'] / stats['total']
    
    def _find_best_spot_region(self, current_region: int, num_regions: int) -> int:
        """Find the region with best spot availability."""
        best_region = current_region
        best_availability = self._get_region_availability(current_region)
        
        for region in range(num_regions):
            if region == current_region:
                continue
            availability = self._get_region_availability(region)
            if availability > best_availability + 0.1:  # 10% better
                best_region = region
                best_availability = availability
        
        return best_region