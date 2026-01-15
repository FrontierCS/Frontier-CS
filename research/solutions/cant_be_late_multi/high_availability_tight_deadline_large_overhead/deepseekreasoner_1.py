import json
from argparse import Namespace
import math
import heapq
from collections import defaultdict
from enum import IntEnum
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class ActionType(IntEnum):
    SPOT = 0
    ON_DEMAND = 1
    NONE = 2
    SWITCH_SPOT = 3
    SWITCH_OD = 4


class RegionState:
    def __init__(self, spot_availability, region_id):
        self.spot_availability = spot_availability
        self.region_id = region_id
        self.spot_blocks = []
        self._compute_blocks()
    
    def _compute_blocks(self):
        """Compute contiguous blocks of spot availability"""
        blocks = []
        start = None
        for i, avail in enumerate(self.spot_availability):
            if avail and start is None:
                start = i
            elif not avail and start is not None:
                blocks.append((start, i - 1))
                start = None
        if start is not None:
            blocks.append((start, len(self.spot_availability) - 1))
        self.spot_blocks = blocks
    
    def get_next_available_spot(self, current_time_step):
        """Find the next available spot block from current time"""
        for start, end in self.spot_blocks:
            if end >= current_time_step:
                return max(start, current_time_step), end
        return None, None
    
    def is_spot_available(self, time_step):
        if 0 <= time_step < len(self.spot_availability):
            return self.spot_availability[time_step]
        return False


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_optimizer"
    
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
        
        # Load and preprocess traces
        self.trace_files = config["trace_files"]
        self.regions = []
        self.spot_price = 0.9701  # $/hr
        self.od_price = 3.06  # $/hr
        self.overhead_steps = int(self.restart_overhead / self.env.gap_seconds)
        
        # Read all traces
        for i, trace_file in enumerate(self.trace_files):
            with open(trace_file, 'r') as f:
                # Read as 0/1 values
                availability = [int(line.strip()) for line in f if line.strip()]
                self.regions.append(RegionState(availability, i))
        
        # Precompute region statistics
        self._precompute_region_stats()
        
        # State tracking
        self.current_region = 0
        self.consecutive_failures = 0
        self.last_action = None
        self.switch_pending = False
        self.force_od_after = None
        
        # Cache for decisions
        self.decision_cache = {}
        
        return self
    
    def _precompute_region_stats(self):
        """Precompute statistics for each region"""
        self.region_stats = []
        for region in self.regions:
            total = len(region.spot_availability)
            available = sum(region.spot_availability)
            ratio = available / total if total > 0 else 0
            
            # Average block length
            avg_block = 0
            if region.spot_blocks:
                lengths = [end - start + 1 for start, end in region.spot_blocks]
                avg_block = sum(lengths) / len(lengths)
            
            self.region_stats.append({
                'availability_ratio': ratio,
                'avg_block_length': avg_block,
                'total_blocks': len(region.spot_blocks)
            })
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is done, return NONE
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE
        
        current_time_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        deadline_step = int(self.deadline / self.env.gap_seconds)
        
        # Calculate remaining work in steps (accounting for overhead)
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_steps_needed = math.ceil(remaining_work / self.env.gap_seconds)
        time_left_steps = deadline_step - current_time_step
        
        # Emergency mode: if we're running out of time, use on-demand
        if time_left_steps <= remaining_steps_needed + 2:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.force_od_after = current_time_step
            return ClusterType.ON_DEMAND
        
        # Check if we're in a forced OD period (after recent failure)
        if self.force_od_after is not None:
            steps_since_force = current_time_step - self.force_od_after
            if steps_since_force < 2:  # Stay on OD for 2 steps after failure
                return ClusterType.ON_DEMAND
            else:
                self.force_od_after = None
        
        # Get current region state
        current_region_state = self.regions[self.current_region]
        
        # If spot is available now and we're not in overhead
        if has_spot and self.remaining_restart_overhead <= 0:
            # Check if we should stay with spot
            if last_cluster_type == ClusterType.SPOT:
                # Continue with spot if next few steps are also available
                next_available = self._check_future_availability(
                    self.current_region, current_time_step, 3
                )
                if next_available >= 2:
                    return ClusterType.SPOT
            
            # Start spot if we were on OD or NONE
            if last_cluster_type != ClusterType.SPOT:
                # Only switch to spot if we have good future availability
                future_avail = self._check_future_availability(
                    self.current_region, current_time_step, 4
                )
                if future_avail >= 3:
                    return ClusterType.SPOT
        
        # If no spot available or poor future availability, consider switching region
        if not has_spot or self.remaining_restart_overhead > 0:
            best_region = self._find_best_region(current_time_step)
            
            if best_region != self.current_region:
                # Check if it's worth switching
                target_region = self.regions[best_region]
                target_has_spot = target_region.is_spot_available(current_time_step)
                
                if target_has_spot:
                    # Switch to spot in new region
                    self.current_region = best_region
                    self.env.switch_region(best_region)
                    return ClusterType.SPOT
                else:
                    # Check future availability in target region
                    future_avail = self._check_future_availability(
                        best_region, current_time_step, 3
                    )
                    if future_avail >= 2:
                        self.current_region = best_region
                        self.env.switch_region(best_region)
                        # Use OD for now, will switch to spot later
                        return ClusterType.ON_DEMAND
        
        # Default to on-demand if nothing else works
        return ClusterType.ON_DEMAND
    
    def _check_future_availability(self, region_idx, start_step, lookahead):
        """Check spot availability in next lookahead steps"""
        region = self.regions[region_idx]
        available_count = 0
        for i in range(lookahead):
            if region.is_spot_available(start_step + i):
                available_count += 1
            else:
                break
        return available_count
    
    def _find_best_region(self, current_time_step):
        """Find the best region to switch to"""
        best_region = self.current_region
        best_score = -1
        
        for i, region in enumerate(self.regions):
            if i == self.current_region:
                continue
            
            # Calculate score based on immediate and future availability
            immediate = 1 if region.is_spot_available(current_time_step) else 0
            
            # Check next few steps
            future_avail = self._check_future_availability(i, current_time_step, 5)
            
            # Consider region reliability
            reliability = self.region_stats[i]['availability_ratio']
            avg_block = self.region_stats[i]['avg_block_length']
            
            # Composite score
            score = (future_avail * 2 + immediate * 3 + 
                    reliability * 10 + avg_block * 0.5)
            
            if score > best_score:
                best_score = score
                best_region = i
        
        return best_region