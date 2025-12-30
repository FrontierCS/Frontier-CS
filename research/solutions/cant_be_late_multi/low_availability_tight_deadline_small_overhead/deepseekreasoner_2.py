import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "efficient_multi_region_scheduler"

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
        
        # Initialize internal state
        self.total_regions = None
        self.current_region = 0
        self.spot_price = 0.9701 / 3600  # $/second
        self.on_demand_price = 3.06 / 3600  # $/second
        self.last_action = ClusterType.NONE
        self.consecutive_spot_failures = 0
        self.region_stats = []
        self.time_step = self.env.gap_seconds
        self.min_safe_time = 2 * self.restart_overhead
        
        return self

    def _initialize_region_stats(self):
        """Initialize statistics for each region"""
        if self.total_regions is None:
            self.total_regions = self.env.get_num_regions()
            self.region_stats = []
            for _ in range(self.total_regions):
                self.region_stats.append({
                    'spot_available': False,
                    'spot_used': 0,
                    'failures': 0,
                    'last_checked': -1
                })

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        """Update statistics for current region"""
        if region_idx < len(self.region_stats):
            stats = self.region_stats[region_idx]
            stats['spot_available'] = has_spot
            stats['last_checked'] = self.env.elapsed_seconds
            if not has_spot:
                stats['failures'] += 1

    def _calculate_remaining_work(self) -> float:
        """Calculate remaining work in seconds"""
        completed = sum(self.task_done_time) if self.task_done_time else 0
        return max(0.0, self.task_duration - completed)

    def _calculate_remaining_time(self) -> float:
        """Calculate remaining time until deadline in seconds"""
        return max(0.0, self.deadline - self.env.elapsed_seconds)

    def _calculate_required_rate(self) -> float:
        """Calculate minimum work rate required to meet deadline"""
        remaining_work = self._calculate_remaining_work()
        remaining_time = self._calculate_remaining_time()
        
        if remaining_time <= 0 or remaining_work <= 0:
            return float('inf')
        
        # Account for potential restart overhead
        effective_time = remaining_time - self.restart_overhead
        if effective_time <= 0:
            return float('inf')
        
        return remaining_work / effective_time

    def _should_use_ondemand(self) -> bool:
        """Determine if we should switch to on-demand based on time constraints"""
        remaining_work = self._calculate_remaining_work()
        remaining_time = self._calculate_remaining_time()
        
        # If we're very close to deadline, use on-demand
        if remaining_time < self.min_safe_time:
            return True
            
        # Calculate if we can afford spot failures
        required_rate = self._calculate_required_rate()
        
        # If required rate is high, use on-demand
        if required_rate > 0.9:  # Need 90% efficiency
            return True
            
        # If we've had many consecutive spot failures
        if self.consecutive_spot_failures >= 3:
            return True
            
        return False

    def _find_best_region(self, current_region: int, has_spot: bool) -> int:
        """Find the best region to switch to"""
        self._initialize_region_stats()
        
        # Update current region stats
        self._update_region_stats(current_region, has_spot)
        
        # If current region has spot and we're not in critical time, stay
        if (has_spot and 
            not self._should_use_ondemand() and 
            self.consecutive_spot_failures < 2):
            return current_region
        
        # Check other regions
        best_region = current_region
        best_score = -1
        
        for region in range(self.total_regions):
            if region == current_region:
                continue
                
            stats = self.region_stats[region]
            # Prefer regions that recently had spot available
            if stats['last_checked'] > 0:
                time_since_check = self.env.elapsed_seconds - stats['last_checked']
                if time_since_check < 3600:  # Within last hour
                    if stats['spot_available']:
                        score = 1.0 / (stats['failures'] + 1)
                        if score > best_score:
                            best_score = score
                            best_region = region
        
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize region stats on first call
        if self.total_regions is None:
            self.total_regions = self.env.get_num_regions()
            self.region_stats = [{'spot_available': False, 'spot_used': 0, 
                                  'failures': 0, 'last_checked': -1} 
                                 for _ in range(self.total_regions)]
        
        current_region = self.env.get_current_region()
        remaining_work = self._calculate_remaining_work()
        remaining_time = self._calculate_remaining_time()
        
        # Check if task is already completed
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Check if deadline has passed
        if remaining_time <= 0:
            return ClusterType.NONE
        
        # Update region statistics
        self._update_region_stats(current_region, has_spot)
        
        # Check if we should switch regions
        best_region = self._find_best_region(current_region, has_spot)
        if best_region != current_region and remaining_time > self.restart_overhead:
            self.env.switch_region(best_region)
            current_region = best_region
            # Update has_spot for new region (will be correct in next iteration)
            has_spot = self.region_stats[current_region]['spot_available']
            self.consecutive_spot_failures = 0
        
        # Determine if we need to use on-demand
        use_ondemand = self._should_use_ondemand()
        
        # Reset spot failure counter if we're using on-demand
        if use_ondemand:
            self.consecutive_spot_failures = 0
        elif not has_spot:
            self.consecutive_spot_failures += 1
        
        # Calculate if we have enough time for overhead
        effective_time_needed = remaining_work
        if (last_cluster_type != ClusterType.ON_DEMAND and use_ondemand and
            self.remaining_restart_overhead <= 0):
            effective_time_needed += self.restart_overhead
        
        # Make decision
        if use_ondemand:
            return ClusterType.ON_DEMAND
        elif has_spot:
            self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        else:
            # No spot available, wait for next time step
            return ClusterType.NONE