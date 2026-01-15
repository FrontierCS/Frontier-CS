import json
from argparse import Namespace
from typing import List
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_multi_region"

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
        self.spot_ratio = self.spot_price / self.ondemand_price
        self.gap_hours = self.env.gap_seconds / 3600.0
        self.overhead_hours = self.restart_overhead / 3600.0
        
        # Track region statistics
        self.region_spot_counts = [0] * self.env.get_num_regions()
        self.region_total_counts = [0] * self.env.get_num_regions()
        self.last_spot_available = False
        self.consecutive_no_spot = 0
        self.region_switch_count = 0
        self.last_region = self.env.get_current_region()
        
        # State machine
        self.state = "EXPLORE"  # or "EXPLOIT"
        self.best_region = None
        self.confidence = [0] * self.env.get_num_regions()
        
        return self

    def _compute_remaining_work(self) -> float:
        """Compute remaining work in hours"""
        done = sum(self.task_done_time) / 3600.0
        return self.task_duration / 3600.0 - done

    def _compute_time_left(self) -> float:
        """Compute time left until deadline in hours"""
        elapsed = self.env.elapsed_seconds / 3600.0
        return self.deadline / 3600.0 - elapsed

    def _should_panic(self) -> bool:
        """Check if we need to switch to on-demand to meet deadline"""
        remaining_work = self._compute_remaining_work()
        time_left = self._compute_time_left()
        
        # Conservative estimate: assume worst-case spot availability
        min_progress_per_hour = self.gap_hours - self.overhead_hours
        hours_needed = remaining_work / min_progress_per_hour if min_progress_per_hour > 0 else float('inf')
        
        # Add safety margin
        return hours_needed > time_left * 0.8

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        """Update statistics for a region"""
        self.region_total_counts[region_idx] += 1
        if has_spot:
            self.region_spot_counts[region_idx] += 1
        
        # Update confidence score (weighted average)
        if self.region_total_counts[region_idx] > 0:
            reliability = self.region_spot_counts[region_idx] / self.region_total_counts[region_idx]
            weight = min(self.region_total_counts[region_idx] / 10.0, 1.0)
            self.confidence[region_idx] = weight * reliability + (1 - weight) * self.confidence[region_idx]

    def _find_best_region(self, current_region: int) -> int:
        """Find the best region to switch to"""
        best_score = -1
        best_region = current_region
        
        for i in range(self.env.get_num_regions()):
            if self.region_total_counts[i] == 0:
                score = 0.5  # Default for unexplored regions
            else:
                reliability = self.region_spot_counts[i] / self.region_total_counts[i]
                # Prefer regions with high reliability and some history
                score = reliability * min(1.0, self.region_total_counts[i] / 5.0)
            
            if score > best_score:
                best_score = score
                best_region = i
        
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current region and update statistics
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)
        
        # Track region switches
        if current_region != self.last_region:
            self.region_switch_count += 1
            self.last_region = current_region
        
        # Update consecutive no-spot counter
        if has_spot:
            self.consecutive_no_spot = 0
            self.last_spot_available = True
        else:
            self.consecutive_no_spot += 1
            self.last_spot_available = False
        
        # Check if we need to panic
        if self._should_panic():
            # Stay in current region, use on-demand
            return ClusterType.ON_DEMAND
        
        # Adaptive exploration/exploitation
        remaining_work = self._compute_remaining_work()
        time_left = self._compute_time_left()
        
        # Determine if we should explore or exploit
        total_samples = sum(self.region_total_counts)
        explore_threshold = max(0.3, 1.0 - total_samples / 100.0)
        
        if self.best_region is None or self.state == "EXPLORE":
            # Exploration phase
            if total_samples < 20 or self.consecutive_no_spot > 2:
                # Switch to a less-explored region
                least_samples = float('inf')
                next_region = current_region
                for i in range(self.env.get_num_regions()):
                    if self.region_total_counts[i] < least_samples:
                        least_samples = self.region_total_counts[i]
                        next_region = i
                
                if next_region != current_region:
                    self.env.switch_region(next_region)
                    self.state = "EXPLORE"
                else:
                    self.state = "EXPLOIT"
                    self.best_region = self._find_best_region(current_region)
            else:
                self.state = "EXPLOIT"
                self.best_region = self._find_best_region(current_region)
        
        # If we're in exploit mode and current region isn't best, consider switching
        if (self.state == "EXPLOIT" and self.best_region is not None and 
            current_region != self.best_region and self.consecutive_no_spot > 1):
            
            # Only switch if we have time and it seems worthwhile
            if time_left > remaining_work * 1.5:
                self.env.switch_region(self.best_region)
                current_region = self.best_region
        
        # Decision logic
        if has_spot:
            # Use spot if available
            return ClusterType.SPOT
        else:
            # No spot available, consider options
            
            # If we have plenty of time, wait for spot
            if time_left > remaining_work * 2.0 and self.consecutive_no_spot < 3:
                return ClusterType.NONE
            
            # Otherwise use on-demand
            return ClusterType.ON_DEMAND