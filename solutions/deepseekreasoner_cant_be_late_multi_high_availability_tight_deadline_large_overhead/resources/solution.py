import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_spot_optimizer"

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
        
        # Initialize tracking structures
        self.region_stats = []
        self.spot_price = 0.9701 / 3600  # $/second
        self.ondemand_price = 3.06 / 3600  # $/second
        self.time_step = None
        self.last_decision = None
        self.consecutive_spot_fails = 0
        self.max_consecutive_fails = 3
        self.spot_success_streak = 0
        self.min_spot_streak = 2
        self.critical_time_threshold = 0.2  # 20% of remaining time
        
        return self

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        """Update statistics for regions."""
        if not hasattr(self, 'region_stats'):
            return
            
        if len(self.region_stats) <= region_idx:
            self.region_stats.extend([{
                'spot_available_count': 0,
                'total_observations': 0,
                'last_observed': -1
            } for _ in range(region_idx - len(self.region_stats) + 1)])
        
        self.region_stats[region_idx]['total_observations'] += 1
        if has_spot:
            self.region_stats[region_idx]['spot_available_count'] += 1
        self.region_stats[region_idx]['last_observed'] = self.env.elapsed_seconds

    def _get_best_region(self, current_region: int, has_spot: bool) -> int:
        """Determine the best region to switch to based on historical data."""
        num_regions = self.env.get_num_regions()
        
        # If we have no stats yet, use round-robin
        if not hasattr(self, 'region_stats') or len(self.region_stats) == 0:
            return (current_region + 1) % num_regions
        
        # Create a list of (score, region_idx) pairs
        region_scores = []
        for idx in range(num_regions):
            if idx >= len(self.region_stats):
                score = 0.5  # Default score for unobserved regions
            else:
                stats = self.region_stats[idx]
                if stats['total_observations'] > 0:
                    # Calculate availability ratio
                    avail_ratio = stats['spot_available_count'] / stats['total_observations']
                    # Penalize regions not recently observed
                    recency_penalty = 0.1 if (self.env.elapsed_seconds - stats['last_observed']) > 3600 else 0
                    score = avail_ratio - recency_penalty
                else:
                    score = 0.5
            
            # Slight preference for current region if it has spot
            if idx == current_region and has_spot:
                score += 0.05
            
            heapq.heappush(region_scores, (-score, idx))
        
        # Return the region with highest score
        return heapq.heappop(region_scores)[1]

    def _should_switch_region(self, current_region: int, has_spot: bool) -> bool:
        """Determine if we should switch regions."""
        if self.env.get_num_regions() <= 1:
            return False
        
        # Don't switch if we're in a restart overhead
        if self.remaining_restart_overhead > 0:
            return False
        
        # Don't switch too frequently
        if self.last_decision == 'switch':
            return False
        
        # If current region has spot and we have a success streak, stay
        if has_spot and self.spot_success_streak >= self.min_spot_streak:
            return False
        
        # If we've had too many consecutive spot fails, consider switching
        if self.consecutive_spot_fails >= self.max_consecutive_fails:
            return True
        
        # Switch if current region doesn't have spot and we're not in critical time
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        time_ratio = remaining_time / max(remaining_work, 1)
        
        if not has_spot and time_ratio > 1.5:
            return True
        
        return False

    def _should_use_ondemand(self, remaining_work: float, remaining_time: float, has_spot: bool) -> bool:
        """Determine if we should use on-demand instances."""
        # Calculate time needed with on-demand
        time_needed_ondemand = remaining_work
        
        # Calculate time needed with spot (pessimistic estimate)
        if has_spot:
            # Assume we might get preempted and lose overhead time
            overhead_fraction = 0.2  # Assume 20% chance of preemption per time unit
            expected_spot_time = remaining_work * (1 + overhead_fraction)
        else:
            expected_spot_time = float('inf')
        
        # Critical condition: if we're running out of time
        time_ratio = remaining_time / max(remaining_work, 1)
        
        # Use on-demand if:
        # 1. We're in critical time (less than threshold slack)
        if time_ratio < 1 + self.critical_time_threshold:
            return True
        
        # 2. We've had too many consecutive spot failures
        if self.consecutive_spot_fails >= self.max_consecutive_fails:
            return True
        
        # 3. Spot is not available and we need to make progress
        if not has_spot and remaining_work > 0:
            return True
        
        # 4. The cost benefit isn't worth the risk
        cost_ondemand = time_needed_ondemand * self.ondemand_price
        cost_spot = expected_spot_time * self.spot_price
        risk_premium = cost_ondemand / max(cost_spot, 0.001)
        
        if risk_premium < 1.3:  # On-demand is less than 30% more expensive than risky spot
            return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Initialize time step on first call
        if self.time_step is None:
            self.time_step = self.env.gap_seconds
        
        # Update region statistics
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)
        
        # Calculate progress metrics
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # Check if we're done or out of time
        if remaining_work <= 0:
            return ClusterType.NONE
        
        if remaining_time <= 0:
            return ClusterType.NONE
        
        # Handle restart overhead
        if self.remaining_restart_overhead > 0:
            self.last_decision = 'wait'
            return ClusterType.NONE
        
        # Check if we should switch regions
        if self._should_switch_region(current_region, has_spot):
            best_region = self._get_best_region(current_region, has_spot)
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.last_decision = 'switch'
                self.consecutive_spot_fails = 0
                self.spot_success_streak = 0
                # After switching, we need to wait for the restart overhead
                return ClusterType.NONE
        
        # Determine if we should use on-demand
        if self._should_use_ondemand(remaining_work, remaining_time, has_spot):
            self.last_decision = 'ondemand'
            self.consecutive_spot_fails = 0
            self.spot_success_streak = 0
            return ClusterType.ON_DEMAND
        
        # Use spot if available
        if has_spot:
            self.last_decision = 'spot'
            self.consecutive_spot_fails = 0
            self.spot_success_streak += 1
            return ClusterType.SPOT
        
        # If spot not available and we shouldn't use on-demand, wait
        self.last_decision = 'wait'
        self.consecutive_spot_fails += 1 if last_cluster_type == ClusterType.SPOT else 0
        self.spot_success_streak = 0
        return ClusterType.NONE
