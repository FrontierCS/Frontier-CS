import json
from argparse import Namespace
import math
from typing import List, Tuple, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with spot price forecasting."""
    
    NAME = "my_strategy"
    
    def __init__(self, args):
        super().__init__(args)
        self.region_stats = {}
        self.current_strategy = "conservative"
        self.spot_use_count = 0
        self.od_use_count = 0
        self.last_action = ClusterType.NONE
        self.consecutive_failures = 0
        self.region_switch_count = 0
        self.spot_history = []
        self.optimal_schedule = None
        
    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Initialize region statistics
        self.region_stats = {
            i: {
                'spot_available_count': 0,
                'total_steps': 0,
                'consecutive_available': 0,
                'max_consecutive': 0,
                'current_consecutive': 0,
                'last_available': False
            }
            for i in range(9)
        }
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        gap = 3600.0  # 1 hour gap as per problem
        
        # Update region statistics
        self._update_region_stats(current_region, has_spot)
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - elapsed
        time_per_step = gap
        
        # Check if we're in restart overhead
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time
        if remaining_time <= remaining_work + 2 * self.restart_overhead:
            # Switch to most reliable region if not already there
            best_region = self._find_most_reliable_region()
            if best_region != current_region:
                self.env.switch_region(best_region)
                return ClusterType.NONE
            # Use on-demand to guarantee progress
            return ClusterType.ON_DEMAND
        
        # Calculate safe time margin
        safe_margin = 4 * self.restart_overhead  # 4 restarts worth of buffer
        
        # Strategic decision making
        if remaining_time - remaining_work > safe_margin:
            # We have enough time to be aggressive with spot
            return self._aggressive_strategy(current_region, has_spot, remaining_work, remaining_time)
        else:
            # Use conservative strategy when time is tight
            return self._conservative_strategy(current_region, has_spot, remaining_work, remaining_time)
    
    def _update_region_stats(self, region_idx: int, has_spot: bool):
        """Update statistics for the current region."""
        stats = self.region_stats[region_idx]
        stats['total_steps'] += 1
        stats['last_available'] = has_spot
        
        if has_spot:
            stats['spot_available_count'] += 1
            stats['current_consecutive'] += 1
            stats['consecutive_available'] = max(stats['consecutive_available'], 
                                                stats['current_consecutive'])
        else:
            stats['current_consecutive'] = 0
    
    def _find_most_reliable_region(self) -> int:
        """Find the region with highest spot availability rate."""
        best_region = 0
        best_score = -1
        
        for region_idx, stats in self.region_stats.items():
            if stats['total_steps'] > 0:
                availability_rate = stats['spot_available_count'] / stats['total_steps']
                # Prefer regions with recent availability
                recent_bonus = 0.1 if stats['last_available'] else 0
                score = availability_rate + recent_bonus
                
                if score > best_score:
                    best_score = score
                    best_region = region_idx
        
        return best_region
    
    def _aggressive_strategy(self, region_idx: int, has_spot: bool, 
                           remaining_work: float, remaining_time: float) -> ClusterType:
        """Use spot aggressively when we have time buffer."""
        gap = 3600.0
        
        # If spot is available, use it
        if has_spot:
            self.spot_use_count += 1
            self.consecutive_failures = 0
            return ClusterType.SPOT
        
        # Spot not available, check if we should switch region
        self.consecutive_failures += 1
        
        # If we've had multiple failures in this region, consider switching
        if self.consecutive_failures >= 2:
            # Find a better region
            best_region = self._find_most_reliable_region()
            if best_region != region_idx:
                self.env.switch_region(best_region)
                self.region_switch_count += 1
                self.consecutive_failures = 0
                return ClusterType.NONE
        
        # If we can't switch or don't want to, use on-demand occasionally
        # Use on-demand about 20% of the time when spot isn't available
        if self.consecutive_failures % 5 == 0:
            self.od_use_count += 1
            return ClusterType.ON_DEMAND
        
        # Otherwise, wait
        return ClusterType.NONE
    
    def _conservative_strategy(self, region_idx: int, has_spot: bool,
                             remaining_work: float, remaining_time: float) -> ClusterType:
        """Use conservative strategy when time is tight."""
        gap = 3600.0
        
        # Calculate minimum steps needed
        min_steps_needed = math.ceil(remaining_work / gap)
        available_steps = math.floor(remaining_time / gap)
        
        # If we have just enough time, use on-demand
        if available_steps <= min_steps_needed + 2:  # Small buffer
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have some buffer, use it
        if has_spot and available_steps > min_steps_needed + 3:
            return ClusterType.SPOT
        
        # If spot not available but we have buffer, wait for it
        if available_steps > min_steps_needed + 4:
            # Check other regions
            best_region = self._find_most_reliable_region()
            if best_region != region_idx and self.region_stats[best_region]['last_available']:
                self.env.switch_region(best_region)
                return ClusterType.NONE
            
            # Wait for spot in current region
            return ClusterType.NONE
        
        # Otherwise, use on-demand
        return ClusterType.ON_DEMAND
