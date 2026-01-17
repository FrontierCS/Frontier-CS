import json
from argparse import Namespace
from typing import List, Tuple
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_dynamic"

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
        
        # Initialize strategy state
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        
        # Track region statistics
        self.region_stats = []  # Will be initialized in first _step
        self.initialized = False
        
        # State tracking
        self.consecutive_failures = 0
        self.last_region = -1
        self.last_action = ClusterType.NONE
        self.work_done = 0.0
        self.time_used = 0.0
        
        return self

    def _initialize_regions(self, num_regions: int):
        """Initialize region statistics tracking."""
        self.region_stats = []
        for _ in range(num_regions):
            self.region_stats.append({
                'spot_available': 0,
                'total_observed': 0,
                'reliability': 0.0,
                'last_observed': -1,
                'consecutive_available': 0,
                'consecutive_unavailable': 0
            })
        self.initialized = True

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        """Update statistics for a region."""
        stats = self.region_stats[region_idx]
        stats['total_observed'] += 1
        if has_spot:
            stats['spot_available'] += 1
            stats['consecutive_available'] += 1
            stats['consecutive_unavailable'] = 0
        else:
            stats['consecutive_unavailable'] += 1
            stats['consecutive_available'] = 0
        
        # Update reliability with exponential moving average
        alpha = 0.1
        current_reliability = 1.0 if has_spot else 0.0
        if stats['total_observed'] == 1:
            stats['reliability'] = current_reliability
        else:
            stats['reliability'] = (alpha * current_reliability + 
                                  (1 - alpha) * stats['reliability'])
        stats['last_observed'] = self.env.elapsed_seconds

    def _get_best_region(self, current_region: int, has_spot: bool) -> int:
        """Select the best region to run in."""
        num_regions = self.env.get_num_regions()
        
        # If current region has spot, consider staying
        if has_spot and self.region_stats[current_region]['reliability'] > 0.7:
            return current_region
        
        # Calculate scores for each region
        scores = []
        for idx in range(num_regions):
            if idx == current_region:
                continue
                
            stats = self.region_stats[idx]
            if stats['total_observed'] == 0:
                # Prioritize unexplored regions
                score = 1.0
            else:
                # Score based on reliability and recent observations
                reliability = stats['reliability']
                recency = 1.0 / (1.0 + self.env.elapsed_seconds - stats['last_observed'])
                score = reliability * 0.7 + recency * 0.3
            
            scores.append((score, idx))
        
        if not scores:
            return current_region
        
        # Return region with highest score
        scores.sort(reverse=True)
        return scores[0][1]

    def _calculate_safety_margin(self) -> float:
        """Calculate safety margin based on remaining time and work."""
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return float('inf')
        
        # Calculate time needed with on-demand (no interruptions)
        time_needed_ondemand = remaining_work
        
        # Calculate time needed with spot (accounting for expected interruptions)
        avg_spot_reliability = 0.0
        count = 0
        for stats in self.region_stats:
            if stats['total_observed'] > 0:
                avg_spot_reliability += stats['reliability']
                count += 1
        
        if count > 0:
            avg_spot_reliability /= count
        else:
            avg_spot_reliability = 0.8  # Default assumption
            
        # Account for restart overheads
        expected_interruptions = (1 - avg_spot_reliability) * (remaining_work / self.env.gap_seconds)
        time_needed_spot = remaining_work + expected_interruptions * self.restart_overhead
        
        # Safety margin: difference between remaining time and spot time needed
        safety_margin = remaining_time - time_needed_spot
        
        return safety_margin

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize region tracking on first call
        if not self.initialized:
            num_regions = self.env.get_num_regions()
            self._initialize_regions(num_regions)
        
        current_region = self.env.get_current_region()
        
        # Update statistics for current region
        self._update_region_stats(current_region, has_spot)
        
        # Check if task is already complete
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE
        
        # Calculate remaining work and time
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # Calculate critical threshold
        time_per_step = self.env.gap_seconds
        steps_remaining = remaining_time / time_per_step
        work_steps_needed = remaining_work / time_per_step
        
        # Emergency mode: must use on-demand to finish on time
        if work_steps_needed > steps_remaining * 0.9:
            # Switch to most reliable region
            best_region = current_region
            best_reliability = self.region_stats[current_region]['reliability']
            for idx in range(self.env.get_num_regions()):
                if self.region_stats[idx]['reliability'] > best_reliability:
                    best_reliability = self.region_stats[idx]['reliability']
                    best_region = idx
            
            if best_region != current_region:
                self.env.switch_region(best_region)
            
            # Reset restart overhead by ensuring clean switch
            if (last_cluster_type != ClusterType.ON_DEMAND and 
                last_cluster_type != ClusterType.NONE):
                # Force a restart by returning NONE first
                if self.remaining_restart_overhead > 0:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Calculate safety margin
        safety_margin = self._calculate_safety_margin()
        
        # If safety margin is low, be more conservative
        if safety_margin < time_per_step * 3:
            # Use on-demand in current region
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Avoid restart overhead if possible
                if self.remaining_restart_overhead > 0:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Normal operation: try to use spot when available
        if has_spot:
            # Check if we should switch to a better region
            best_region = self._get_best_region(current_region, has_spot)
            if best_region != current_region:
                # Only switch if the target region is significantly better
                current_rel = self.region_stats[current_region]['reliability']
                best_rel = self.region_stats[best_region]['reliability']
                
                if (best_rel > current_rel * 1.2 or 
                    self.region_stats[current_region]['consecutive_unavailable'] > 2):
                    self.env.switch_region(best_region)
                    # After switching, use spot if available
                    return ClusterType.SPOT
            
            # Use spot in current region
            self.consecutive_failures = 0
            return ClusterType.SPOT
        else:
            # Spot not available in current region
            self.consecutive_failures += 1
            
            # If too many consecutive failures, try different region
            if self.consecutive_failures > 2:
                best_region = self._get_best_region(current_region, False)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.consecutive_failures = 0
                    # After switching, use spot if we think it's available
                    # Otherwise use on-demand if safety margin is low
                    if safety_margin > time_per_step * 5:
                        return ClusterType.NONE
                    else:
                        return ClusterType.ON_DEMAND
            
            # Decide between on-demand and waiting
            if safety_margin > time_per_step * 2:
                # Can afford to wait
                return ClusterType.NONE
            else:
                # Need to make progress
                if last_cluster_type != ClusterType.ON_DEMAND:
                    if self.remaining_restart_overhead > 0:
                        return ClusterType.NONE
                    else:
                        return ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND