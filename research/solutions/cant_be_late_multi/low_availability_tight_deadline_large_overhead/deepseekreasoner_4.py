import json
from argparse import Namespace
import math
from collections import deque
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        
        # Precompute values
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        
        # Load traces to precompute availability patterns
        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                self.traces.append([int(line.strip()) for line in f])
        
        self.num_regions = len(self.traces)
        self.timesteps = len(self.traces[0]) if self.traces else 0
        
        # Precompute region quality scores
        self.region_scores = []
        for region_idx in range(self.num_regions):
            trace = self.traces[region_idx]
            # Calculate spot availability percentage
            available = sum(trace)
            total = len(trace)
            score = available / total if total > 0 else 0
            self.region_scores.append(score)
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Convert to hours for easier calculations
        hours_remaining = time_remaining / 3600.0
        hours_needed = remaining_work / 3600.0
        
        # If no work left, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time steps remaining
        steps_remaining = int(time_remaining / self.env.gap_seconds)
        
        # Emergency mode: if we're running out of time, use on-demand
        if hours_needed > hours_remaining * 0.8:  # Less than 20% slack
            return ClusterType.ON_DEMAND
        
        # Get current region
        current_region = self.env.get_current_region()
        
        # Check if we should switch regions
        if self._should_switch_region(current_region, steps_remaining):
            # Find best region
            best_region = self._find_best_region(current_region, steps_remaining)
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, we need to restart, so use on-demand if spot not available
                current_region = best_region
                has_spot = self._check_spot_availability(current_region, steps_remaining)
                if has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        # If we have restart overhead pending, use on-demand to avoid wasting time
        if self.remaining_restart_overhead > 0:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have reasonable time buffer, use it
        if has_spot:
            # Calculate how many spot interruptions we can afford
            max_interruptions = int((hours_remaining - hours_needed) / 
                                  (self.restart_overhead / 3600.0))
            
            # Estimate spot reliability in current region
            current_time_step = int(time_elapsed / self.env.gap_seconds)
            if current_time_step < self.timesteps:
                # Look ahead at next few timesteps
                look_ahead = min(10, self.timesteps - current_time_step)
                spot_reliability = sum(
                    self.traces[current_region][current_time_step:current_time_step + look_ahead]
                ) / look_ahead
                
                # Use spot if it's reliable enough or we can afford interruptions
                if spot_reliability > 0.7 or max_interruptions > 3:
                    return ClusterType.SPOT
        
        # Default to on-demand
        return ClusterType.ON_DEMAND

    def _should_switch_region(self, current_region: int, steps_remaining: int) -> bool:
        if self.num_regions <= 1:
            return False
        
        # Don't switch too often to avoid restart overhead
        time_elapsed = self.env.elapsed_seconds
        current_time_step = int(time_elapsed / self.env.gap_seconds)
        
        # Calculate current region's future spot availability
        if current_time_step < self.timesteps:
            future_steps = min(steps_remaining, self.timesteps - current_time_step)
            if future_steps <= 0:
                return False
            
            current_availability = sum(
                self.traces[current_region][current_time_step:current_time_step + future_steps]
            ) / future_steps
            
            # Find best alternative region
            best_alt_availability = 0
            for region in range(self.num_regions):
                if region == current_region:
                    continue
                alt_availability = sum(
                    self.traces[region][current_time_step:current_time_step + future_steps]
                ) / future_steps
                best_alt_availability = max(best_alt_availability, alt_availability)
            
            # Switch only if alternative is significantly better
            return best_alt_availability > current_availability + 0.2
        
        return False

    def _find_best_region(self, current_region: int, steps_remaining: int) -> int:
        time_elapsed = self.env.elapsed_seconds
        current_time_step = int(time_elapsed / self.env.gap_seconds)
        
        best_region = current_region
        best_score = -1
        
        for region in range(self.num_regions):
            if current_time_step < self.timesteps:
                future_steps = min(steps_remaining, self.timesteps - current_time_step)
                if future_steps <= 0:
                    continue
                
                availability = sum(
                    self.traces[region][current_time_step:current_time_step + future_steps]
                ) / future_steps
                
                # Add small penalty for switching to prefer staying
                penalty = 0.1 if region != current_region else 0
                score = availability - penalty
                
                if score > best_score:
                    best_score = score
                    best_region = region
        
        return best_region

    def _check_spot_availability(self, region: int, steps_remaining: int) -> bool:
        time_elapsed = self.env.elapsed_seconds
        current_time_step = int(time_elapsed / self.env.gap_seconds)
        
        if current_time_step < self.timesteps:
            # Check next timestep
            next_step = min(current_time_step, self.timesteps - 1)
            return bool(self.traces[region][next_step])
        
        return False