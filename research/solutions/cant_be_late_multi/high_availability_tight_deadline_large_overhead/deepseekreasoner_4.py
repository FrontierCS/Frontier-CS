import json
from argparse import Namespace
from collections import defaultdict
import math
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with dynamic region selection."""
    
    NAME = "multi_region_adaptive"

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
        
        # Load traces for lookahead capability
        self.traces = []
        self.trace_duration = 0
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file, 'r') as f:
                        # Parse trace: each line contains availability (0/1)
                        trace = []
                        for line in f:
                            line = line.strip()
                            if line:
                                trace.append(int(line))
                        if trace:
                            self.traces.append(trace)
                            self.trace_duration = max(self.trace_duration, len(trace))
                except Exception:
                    # If trace file cannot be read, continue without it
                    pass
        
        # Initialize strategy state
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.hourly_gap = 3600  # 1 hour in seconds
        self.task_duration_hours = float(config["duration"])
        self.deadline_hours = float(config["deadline"])
        self.overhead_hours = float(config["overhead"])
        
        # Region statistics
        self.region_stats = defaultdict(lambda: {
            'spot_available': 0,
            'total_steps': 0,
            'reliability': 1.0
        })
        
        # Current execution state
        self.current_region = 0
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.switch_cooldown = 0
        
        # Lookahead window for planning
        self.lookahead_window = min(12, self.trace_duration)
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update statistics for current region
        if self.env.get_current_region() < len(self.region_stats):
            stats = self.region_stats[self.env.get_current_region()]
            stats['total_steps'] += 1
            if has_spot:
                stats['spot_available'] += 1
            if stats['total_steps'] > 0:
                stats['reliability'] = stats['spot_available'] / stats['total_steps']
        
        # Get current state
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        task_done = sum(self.task_done_time)
        remaining_work = max(0, self.task_duration - task_done)
        remaining_time = max(0, deadline - elapsed)
        
        # Check if we can finish in time with on-demand
        time_needed = remaining_work
        if self.last_action != ClusterType.ON_DEMAND and remaining_work > 0:
            time_needed += self.restart_overhead
        
        # If we're running out of time, switch to on-demand
        if remaining_time < time_needed * 1.2:  # 20% safety margin
            if has_spot and self.last_action == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Calculate progress rate needed
        progress_needed = remaining_work / max(1, remaining_time - self.restart_overhead)
        
        # If we have traces for lookahead, use them for planning
        best_region = current_region
        best_score = -float('inf')
        
        if self.traces and len(self.traces) > 1:
            current_step = int(elapsed // self.hourly_gap)
            
            for region_idx in range(len(self.traces)):
                if region_idx >= self.env.get_num_regions():
                    continue
                    
                # Calculate score for this region
                score = 0
                
                # Reliability score
                rel = self.region_stats[region_idx]['reliability']
                score += rel * 2.0
                
                # Lookahead availability
                if current_step < len(self.traces[region_idx]):
                    future_avail = 0
                    look_steps = min(self.lookahead_window, len(self.traces[region_idx]) - current_step)
                    for i in range(look_steps):
                        if current_step + i < len(self.traces[region_idx]):
                            future_avail += self.traces[region_idx][current_step + i]
                    if look_steps > 0:
                        score += (future_avail / look_steps) * 1.5
                
                # Prefer staying in current region to avoid switch overhead
                if region_idx == current_region:
                    score += 1.0
                
                if score > best_score:
                    best_score = score
                    best_region = region_idx
        
        # Switch region if beneficial and not in cooldown
        if (best_region != current_region and 
            self.switch_cooldown <= 0 and
            len(self.traces) > 1):
            
            # Only switch if the target region has better reliability
            current_rel = self.region_stats[current_region]['reliability']
            target_rel = self.region_stats[best_region]['reliability']
            
            if target_rel > current_rel * 1.2:  # 20% better
                self.env.switch_region(best_region)
                self.current_region = best_region
                self.switch_cooldown = 3  # Don't switch again for 3 steps
                self.last_action = ClusterType.NONE
                return ClusterType.NONE  # Let overhead clear
        
        # Update cooldown
        if self.switch_cooldown > 0:
            self.switch_cooldown -= 1
        
        # Decision logic based on current state
        if has_spot:
            # Use spot if we have buffer time
            buffer_ratio = remaining_time / (remaining_work + self.restart_overhead)
            
            if buffer_ratio > 1.5:  # Good buffer
                if (self.last_action != ClusterType.SPOT and 
                    remaining_work > 0 and
                    self.remaining_restart_overhead <= 0):
                    # Only switch to spot if no overhead pending
                    self.last_action = ClusterType.SPOT
                    return ClusterType.SPOT
                elif self.last_action == ClusterType.SPOT:
                    return ClusterType.SPOT
            
            # Moderate buffer: use spot cautiously
            elif buffer_ratio > 1.2:
                if self.consecutive_failures < 2:
                    self.last_action = ClusterType.SPOT
                    return ClusterType.SPOT
                else:
                    # Too many recent failures, try on-demand
                    self.consecutive_failures = 0
                    self.last_action = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
        
        # Default to on-demand when spot is not available or we need reliability
        if progress_needed > 0.8:  # Need high progress rate
            self.last_action = ClusterType.ON_DEMAND
            self.consecutive_failures = 0
            return ClusterType.ON_DEMAND
        
        # If spot not available and we have time, pause briefly
        if remaining_time > remaining_work * 1.3:
            self.last_action = ClusterType.NONE
            return ClusterType.NONE
        
        # Final fallback
        self.last_action = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND