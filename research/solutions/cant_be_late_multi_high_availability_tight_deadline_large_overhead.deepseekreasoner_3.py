import json
from argparse import Namespace
import heapq
from collections import defaultdict
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "spot_aware_multi_region"

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
        self.hourly_gap = 3600.0  # Assuming 1-hour steps
        
        # State tracking
        self.region_history = defaultdict(list)
        self.current_work_segments = []
        self.last_action = ClusterType.NONE
        self.consecutive_spot_failures = 0
        
        # Pre-computed thresholds
        self.critical_time_threshold = self.task_duration * 1.5  # 1.5x task duration
        self.min_slack_for_spot = self.restart_overhead * 3  # Need 3x overhead as slack
        
        return self

    def _get_remaining_work(self) -> float:
        """Calculate remaining work in seconds."""
        return self.task_duration - sum(self.task_done_time)

    def _get_time_left(self) -> float:
        """Calculate time left until deadline in seconds."""
        return self.deadline - self.env.elapsed_seconds

    def _get_slack_ratio(self) -> float:
        """Calculate slack ratio (time left / remaining work)."""
        remaining_work = self._get_remaining_work()
        if remaining_work <= 0:
            return float('inf')
        time_left = self._get_time_left()
        return time_left / remaining_work

    def _should_use_ondemand(self) -> bool:
        """Determine if we should use on-demand based on current conditions."""
        if self._get_remaining_work() <= 0:
            return False
            
        time_left = self._get_time_left()
        remaining_work = self._get_remaining_work()
        
        # Critical condition: not enough time even without overhead
        if time_left < remaining_work:
            return True
            
        # If we're in the last stretch with minimal slack
        required_with_overhead = remaining_work + self.restart_overhead
        if time_left < required_with_overhead:
            return True
            
        # If we've had repeated spot failures
        if self.consecutive_spot_failures >= 3:
            return True
            
        # If slack ratio is too low
        slack_ratio = self._get_slack_ratio()
        if slack_ratio < 1.2:  # Less than 20% slack
            return True
            
        return False

    def _find_best_region(self, require_spot: bool = False) -> int:
        """Find the best region to switch to."""
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Simple heuristic: try next region if current has no spot
        if require_spot:
            # Round-robin through regions
            next_region = (current_region + 1) % num_regions
            return next_region
        
        # If not requiring spot, stay in current region
        return current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        # Handle pending restart overhead
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Check if task is already complete
        if self._get_remaining_work() <= 0:
            return ClusterType.NONE
        
        # Critical condition: must use on-demand
        if self._should_use_ondemand():
            # If no spot but we want on-demand, just use it in current region
            return ClusterType.ON_DEMAND
        
        # Non-critical: try to use spot if available
        if has_spot:
            # Calculate if we have enough slack for potential preemption
            slack_ratio = self._get_slack_ratio()
            if slack_ratio > 1.5:  # Good amount of slack
                return ClusterType.SPOT
            elif slack_ratio > 1.2:  # Moderate slack
                # Use spot but be cautious
                if self.consecutive_spot_failures == 0:
                    return ClusterType.SPOT
                else:
                    # After failures, be more conservative
                    return ClusterType.ON_DEMAND
            else:
                # Low slack, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            # Only switch if we have good slack
            slack_ratio = self._get_slack_ratio()
            if slack_ratio > 2.0:  # Plenty of slack to explore
                # Switch to another region hoping for spot
                next_region = self._find_best_region(require_spot=True)
                if next_region != self.env.get_current_region():
                    self.env.switch_region(next_region)
                    # After switching, we'll get overhead, so return NONE
                    # Actually, we return NONE to let the switch happen without starting instance
                    return ClusterType.NONE
                else:
                    # All regions checked, use on-demand
                    return ClusterType.ON_DEMAND
            else:
                # Not enough slack to switch, use on-demand in current region
                return ClusterType.ON_DEMAND
