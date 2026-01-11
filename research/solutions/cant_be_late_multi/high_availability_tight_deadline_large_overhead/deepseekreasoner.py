import json
from argparse import Namespace
from typing import List
import numpy as np
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        
        # Store config for reference
        self._trace_files = config["trace_files"]
        self._deadline_h = float(config["deadline"])
        self._duration_h = float(config["duration"])
        self._overhead_h = float(config["overhead"])
        
        # Convert to seconds for easier calculations
        self._deadline_s = self._deadline_h * 3600
        self._duration_s = self._duration_h * 3600
        self._overhead_s = self._overhead_h * 3600
        
        # Constants from problem description
        self._spot_price = 0.9701  # $/hr
        self._ondemand_price = 3.06  # $/hr
        
        # State tracking
        self._last_action = None
        self._current_region = 0
        self._region_spot_history = {}
        self._time_step = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update state
        self._time_step += 1
        self._current_region = self.env.get_current_region()
        
        # Store spot availability history
        if self._current_region not in self._region_spot_history:
            self._region_spot_history[self._current_region] = []
        self._region_spot_history[self._current_region].append(has_spot)
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we're in overhead period, wait it out
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Calculate conservative time needed
        # Assume worst case: we might need to restart once more
        effective_remaining_time = remaining_time - min(self.restart_overhead, remaining_time * 0.1)
        
        # Calculate minimum time needed with on-demand (no interruptions)
        min_time_needed = remaining_work
        
        # Emergency mode: if we're running out of time, use on-demand
        safety_margin = max(self.restart_overhead * 2, 3600)  # 2 overheads or 1 hour
        
        if effective_remaining_time < min_time_needed + safety_margin:
            return ClusterType.ON_DEMAND
        
        # Calculate spot reliability in current region
        current_region_history = self._region_spot_history.get(self._current_region, [])
        if len(current_region_history) > 10:
            spot_reliability = sum(current_region_history[-10:]) / 10
        else:
            spot_reliability = 0.7  # Conservative default
        
        # If spot is available and reasonably reliable, use it
        if has_spot and spot_reliability > 0.6:
            # Check if we should switch to a better region
            best_region = self._find_best_region()
            if best_region != self._current_region:
                # Only switch if significantly better
                current_score = self._calculate_region_score(self._current_region, has_spot)
                best_score = self._calculate_region_score(best_region, True)
                if best_score > current_score * 1.2:  # 20% better
                    self.env.switch_region(best_region)
                    # After switching, we need to restart, so use NONE this step
                    return ClusterType.NONE
            return ClusterType.SPOT
        
        # Spot not available or unreliable
        if not has_spot:
            # Try to find a region with spot available
            best_region = self._find_best_region()
            if best_region != self._current_region:
                self.env.switch_region(best_region)
                return ClusterType.NONE
        
        # Use on-demand as fallback
        return ClusterType.ON_DEMAND
    
    def _find_best_region(self) -> int:
        """Find the region with best expected spot availability."""
        num_regions = self.env.get_num_regions()
        best_region = self._current_region
        best_score = -float('inf')
        
        for region in range(num_regions):
            score = self._calculate_region_score(region, True)  # Assume spot available for scoring
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region
    
    def _calculate_region_score(self, region: int, has_spot_now: bool) -> float:
        """Calculate a score for choosing a region."""
        score = 0
        
        # Prefer regions with recent spot availability
        history = self._region_spot_history.get(region, [])
        if history:
            recent_history = history[-5:] if len(history) >= 5 else history
            spot_reliability = sum(recent_history) / len(recent_history)
            score += spot_reliability * 10
        
        # Bonus for current region (avoid switching overhead)
        if region == self._current_region:
            score += 2
        
        # Bonus if spot is currently available
        if has_spot_now:
            score += 5
        
        return score