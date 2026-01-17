import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "multi_region_adaptive"

    def __init__(self, args):
        super().__init__(args)
        self.region_availability = []
        self.trace_length = 0
        self.gap_seconds = 0
        self.on_demand_price = 3.06 / 3600  # $/second
        self.spot_price = 0.9701 / 3600  # $/second
        self.last_action = None
        self.region_switch_pending = False
        self.spot_unavailable_counter = {}
        self.region_stats = []
        self.priority_queue = []
        self.initialized = False
        self.spot_availability_cache = {}

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
        
        # Read and preprocess trace files
        self.region_availability = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                # Read all lines and convert to boolean
                availability = [line.strip().lower() == 'true' for line in f if line.strip()]
                self.region_availability.append(availability)
        
        if self.region_availability:
            self.trace_length = len(self.region_availability[0])
            
        # Initialize region stats
        num_regions = len(self.region_availability)
        self.region_stats = [{
            'spot_available_count': sum(self.region_availability[i]),
            'spot_unavailable_streak': 0,
            'last_spot_time': -1,
            'score': 0.0
        } for i in range(num_regions)]
        
        # Initialize spot unavailable counters
        self.spot_unavailable_counter = {i: 0 for i in range(num_regions)}
        
        self.initialized = True
        return self

    def _initialize_step(self):
        """Initialize or update state at beginning of step."""
        if not hasattr(self, 'gap_seconds'):
            self.gap_seconds = self.env.gap_seconds
            
        current_region = self.env.get_current_region()
        
        # Update region stats based on current spot availability
        if hasattr(self, 'last_has_spot'):
            # Update streak information
            if not self.last_has_spot:
                self.region_stats[current_region]['spot_unavailable_streak'] += 1
            else:
                self.region_stats[current_region]['spot_unavailable_streak'] = 0
                self.region_stats[current_region]['last_spot_time'] = self.env.elapsed_seconds

    def _calculate_region_score(self, region_idx: int, lookahead_steps: int = 5) -> float:
        """Calculate score for a region based on spot availability patterns."""
        if region_idx >= len(self.region_availability):
            return float('-inf')
            
        current_time = self.env.elapsed_seconds
        current_step = int(current_time / self.gap_seconds)
        
        # Check cache
        cache_key = (region_idx, current_step)
        if cache_key in self.spot_availability_cache:
            return self.spot_availability_cache[cache_key]
        
        if current_step >= self.trace_length:
            score = 0.0
        else:
            # Calculate immediate and near-future spot availability
            future_steps = min(lookahead_steps, self.trace_length - current_step)
            spot_count = 0
            for i in range(future_steps):
                if current_step + i < len(self.region_availability[region_idx]):
                    if self.region_availability[region_idx][current_step + i]:
                        spot_count += 1
            
            # Penalize regions with recent long unavailability streaks
            streak_penalty = min(self.region_stats[region_idx]['spot_unavailable_streak'] * 0.1, 1.0)
            
            # Base score on spot availability density
            base_score = spot_count / max(future_steps, 1)
            
            # Adjust score based on overall availability in this region
            total_available = self.region_stats[region_idx]['spot_available_count']
            total_steps = min(self.trace_length, int(self.deadline / self.gap_seconds))
            long_term_score = total_available / max(total_steps, 1)
            
            # Combine scores
            score = 0.6 * base_score + 0.4 * long_term_score - streak_penalty
            
            # Bonus for regions we're already in (avoid switching cost)
            if region_idx == self.env.get_current_region() and self.last_action != ClusterType.NONE:
                score += 0.2
        
        self.spot_availability_cache[cache_key] = score
        return score

    def _get_best_region(self) -> int:
        """Find the best region to switch to based on current conditions."""
        current_region = self.env.get_current_region()
        best_region = current_region
        best_score = self._calculate_region_score(current_region)
        
        # Check other regions
        for region in range(self.env.get_num_regions()):
            if region == current_region:
                continue
                
            score = self._calculate_region_score(region)
            if score > best_score:
                # Only switch if significantly better to avoid overhead
                if score > best_score + 0.15:  # Threshold to trigger switch
                    best_score = score
                    best_region = region
        
        return best_region

    def _should_switch_to_ondemand(self) -> bool:
        """Determine if we should switch to on-demand based on deadline pressure."""
        if not hasattr(self, 'gap_seconds'):
            return False
            
        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If we're very close to deadline, use on-demand
        if remaining_time < self.restart_overhead * 2:
            return True
            
        # Calculate conservative estimate of time needed with spot
        # Assume we might face restart overheads
        estimated_time_needed = remaining_work + self.restart_overhead * 2
        
        # If we're cutting it close, switch to on-demand
        safety_margin = self.gap_seconds * 3  # 3 time steps as buffer
        if remaining_time - estimated_time_needed < safety_margin:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_step()
        
        # Store current spot availability for next step
        self.last_has_spot = has_spot
        
        # If task is complete, return NONE
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE
        
        # Check if we're in danger of missing deadline
        if self._should_switch_to_ondemand():
            # If switching region would help and we have time, try that first
            if self.env.elapsed_seconds < self.deadline - self.restart_overhead * 3:
                best_region = self._get_best_region()
                if best_region != self.env.get_current_region():
                    self.env.switch_region(best_region)
                    # After switch, we need to restart
                    return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Get best region considering spot availability
        best_region = self._get_best_region()
        current_region = self.env.get_current_region()
        
        # Switch region if beneficial
        if best_region != current_region:
            # Only switch if we're not in the middle of important work
            if self.last_action not in [ClusterType.SPOT, ClusterType.ON_DEMAND] or \
               self.remaining_restart_overhead > 0:
                self.env.switch_region(best_region)
                self.region_switch_pending = True
        
        # Determine cluster type based on spot availability and conditions
        current_region = self.env.get_current_region()
        
        if has_spot:
            # Use spot if available, but be cautious if we have pending restart overhead
            if self.remaining_restart_overhead > 0:
                # If we have restart overhead, consider using on-demand to avoid wasting time
                remaining_time = self.deadline - self.env.elapsed_seconds
                if remaining_time < self.gap_seconds * 4:  # Very tight schedule
                    return ClusterType.ON_DEMAND
            
            # Check spot availability pattern in this region
            current_step = int(self.env.elapsed_seconds / self.gap_seconds)
            if current_step < self.trace_length - 1:
                # Look ahead a bit to avoid spot that will disappear soon
                lookahead = min(3, self.trace_length - current_step - 1)
                future_available = all(
                    self.region_availability[current_region][current_step + i + 1]
                    for i in range(lookahead)
                )
                if not future_available and lookahead > 0:
                    # Spot will disappear soon, consider on-demand if schedule is tight
                    remaining_work = self.task_duration - sum(self.task_done_time)
                    if remaining_work > self.gap_seconds * 2:
                        return ClusterType.ON_DEMAND
            
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        else:
            # Spot not available in current region
            # Check if we should wait or use on-demand
            remaining_time = self.deadline - self.env.elapsed_seconds
            remaining_work = self.task_duration - sum(self.task_done_time)
            
            # Estimate if we have time to wait for spot
            time_needed_with_ondemand = remaining_work
            time_needed_with_spot = remaining_work + self.restart_overhead  # Conservative
            
            # If we have plenty of time, wait for spot
            if remaining_time > time_needed_with_spot * 1.5:
                self.last_action = ClusterType.NONE
                return ClusterType.NONE
            else:
                # Use on-demand to ensure we meet deadline
                self.last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND