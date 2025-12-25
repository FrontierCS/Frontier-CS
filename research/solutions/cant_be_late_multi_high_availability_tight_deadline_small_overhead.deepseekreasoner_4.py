import json
import math
from argparse import Namespace
from enum import IntEnum
from typing import List, Dict, Tuple

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
        
        # Initialize state
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.region_stats = {}
        self.last_decision = None
        self.region_history = []
        self.consecutive_failures = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        total_regions = self.env.get_num_regions()
        
        # Calculate critical metrics
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        remaining_time = deadline - elapsed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        gap_seconds = 3600.0  # Fixed time step
        
        # Calculate minimum time needed with on-demand (no overhead)
        min_steps_needed = math.ceil(remaining_work / gap_seconds)
        min_time_needed = min_steps_needed * gap_seconds
        
        # Calculate time needed with overhead considerations
        effective_time_needed = min_time_needed
        if self.remaining_restart_overhead > 0:
            effective_time_needed += self.remaining_restart_overhead
        
        # Emergency mode: must use on-demand to meet deadline
        if remaining_time <= effective_time_needed + gap_seconds:
            return ClusterType.ON_DEMAND
        
        # Record region availability
        if current_region not in self.region_stats:
            self.region_stats[current_region] = {
                'spot_available': has_spot,
                'last_seen': elapsed,
                'availability_score': 1 if has_spot else 0,
                'attempts': 1
            }
        else:
            stats = self.region_stats[current_region]
            stats['spot_available'] = has_spot
            stats['last_seen'] = elapsed
            # Update availability score (exponential moving average)
            alpha = 0.3
            stats['availability_score'] = (alpha * (1 if has_spot else 0) + 
                                         (1 - alpha) * stats['availability_score'])
            stats['attempts'] += 1
        
        # Check if we should switch regions
        should_switch = False
        best_region = current_region
        
        if not has_spot:
            # Find best region to switch to
            for region in range(total_regions):
                if region == current_region:
                    continue
                
                if region not in self.region_stats:
                    # Unknown region, give it a chance
                    best_region = region
                    should_switch = True
                    break
                else:
                    stats = self.region_stats[region]
                    # Prefer regions with high availability scores
                    if stats['availability_score'] > 0.5:
                        best_region = region
                        should_switch = True
                        break
            
            # If no good region found, try least recently seen
            if not should_switch:
                for region in range(total_regions):
                    if region == current_region:
                        continue
                    if region in self.region_stats:
                        if self.region_stats[region]['last_seen'] < elapsed - 3600:
                            best_region = region
                            should_switch = True
                            break
        
        # Switch region if needed
        if should_switch and best_region != current_region:
            self.env.switch_region(best_region)
            # After switching, we need to be conservative
            return ClusterType.ON_DEMAND if remaining_time < min_time_needed * 1.5 else ClusterType.SPOT
        
        # Normal operation decision
        if has_spot:
            # Use spot if we have enough time buffer
            time_buffer = remaining_time - effective_time_needed
            if time_buffer > gap_seconds * 2:  # 2-hour buffer
                return ClusterType.SPOT
            else:
                # Conservative: use on-demand when buffer is small
                return ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            if remaining_time < min_time_needed * 1.2:  # Tight deadline
                return ClusterType.ON_DEMAND
            else:
                # Try switching region next time
                return ClusterType.NONE
