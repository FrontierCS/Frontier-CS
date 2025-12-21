import json
from argparse import Namespace
import math
from typing import List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy that minimizes cost while meeting deadline."""

    NAME = "multi_region_scheduler"

    def __init__(self, args):
        """Initialize the solution."""
        super().__init__(args)
        self.spot_availability = None
        self.region_count = 0
        self.time_step = 3600  # 1 hour in seconds
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.deadline_seconds = 0
        self.task_duration_seconds = 0
        self.overhead_seconds = 0
        self.current_time_idx = 0

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
        
        # Load spot availability traces
        self.spot_availability = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                # Read availability data (assuming one value per line)
                availability = [bool(int(line.strip())) for line in f]
                self.spot_availability.append(availability)
        
        self.region_count = len(self.spot_availability)
        self.deadline_seconds = float(config["deadline"]) * 3600
        self.task_duration_seconds = float(config["duration"]) * 3600
        self.overhead_seconds = float(config["overhead"]) * 3600
        
        return self

    def _get_time_index(self, elapsed_seconds: float) -> int:
        """Convert elapsed seconds to time step index."""
        return int(elapsed_seconds // self.time_step)

    def _get_remaining_time_steps(self, elapsed_seconds: float) -> int:
        """Get remaining time steps until deadline."""
        total_steps = int(self.deadline_seconds // self.time_step)
        current_step = self._get_time_index(elapsed_seconds)
        return max(0, total_steps - current_step)

    def _get_work_done(self) -> float:
        """Get total work done in seconds."""
        return sum(self.task_done_time)

    def _get_remaining_work(self) -> float:
        """Get remaining work in seconds."""
        return max(0, self.task_duration - self._get_work_done())

    def _estimate_best_case_completion(self, current_region: int, has_spot: bool,
                                      time_idx: int) -> Tuple[float, float]:
        """
        Estimate best-case completion time and cost.
        Returns (time_seconds, cost_dollars).
        """
        remaining_work = self._get_remaining_work()
        elapsed = self.env.elapsed_seconds
        
        if remaining_work <= 0:
            return (0, 0)
        
        # Calculate if we need to consider restart overhead
        needs_restart = False
        if (self.env.cluster_type == ClusterType.SPOT and not has_spot) or \
           self.remaining_restart_overhead > 0:
            needs_restart = True
        
        # Calculate effective work per time step
        if needs_restart:
            effective_work = self.time_step - self.overhead_seconds
        else:
            effective_work = self.time_step
        
        # Estimate time to complete with current setup
        steps_needed = math.ceil(remaining_work / effective_work)
        time_needed = steps_needed * self.time_step
        
        # Estimate cost
        if has_spot:
            cost_per_step = self.spot_price * (self.time_step / 3600)
        else:
            cost_per_step = self.ondemand_price * (self.time_step / 3600)
        
        estimated_cost = steps_needed * cost_per_step
        
        return (time_needed, estimated_cost)

    def _find_best_region(self, current_time_idx: int) -> Tuple[int, bool, float]:
        """
        Find the best region to switch to.
        Returns (region_index, has_spot_now, future_availability_score).
        """
        best_region = self.env.get_current_region()
        best_score = -1
        best_has_spot = False
        
        for region_idx in range(self.region_count):
            if region_idx == self.env.get_current_region():
                continue
                
            # Check current availability
            has_spot_now = False
            if current_time_idx < len(self.spot_availability[region_idx]):
                has_spot_now = self.spot_availability[region_idx][current_time_idx]
            
            # Calculate future availability score (next 5 time steps)
            future_score = 0
            lookahead = min(5, len(self.spot_availability[region_idx]) - current_time_idx)
            
            for i in range(lookahead):
                time_idx = current_time_idx + i
                if time_idx < len(self.spot_availability[region_idx]):
                    if self.spot_availability[region_idx][time_idx]:
                        future_score += 1.0 / (i + 1)  # Weight by proximity
            
            total_score = future_score
            if has_spot_now:
                total_score += 2.0  # Bonus for immediate availability
            
            if total_score > best_score:
                best_score = total_score
                best_region = region_idx
                best_has_spot = has_spot_now
        
        return (best_region, best_has_spot, best_score)

    def _should_switch_region(self, current_region: int, current_has_spot: bool,
                             time_idx: int) -> bool:
        """Determine if we should switch to another region."""
        if self.region_count <= 1:
            return False
        
        remaining_work = self._get_remaining_work()
        remaining_time = self.deadline_seconds - self.env.elapsed_seconds
        
        # If we're very close to deadline, don't switch
        if remaining_time < 2 * self.time_step:
            return False
        
        # If current region has spot, only switch if other region is much better
        if current_has_spot:
            best_region, best_has_spot, best_score = self._find_best_region(time_idx)
            if best_region != current_region and best_score > 3.0:  # Threshold
                return True
            return False
        
        # Current region doesn't have spot - check if any other region does
        for region_idx in range(self.region_count):
            if region_idx == current_region:
                continue
            if time_idx < len(self.spot_availability[region_idx]):
                if self.spot_availability[region_idx][time_idx]:
                    return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        time_idx = self._get_time_index(self.env.elapsed_seconds)
        
        # Get remaining work and time
        remaining_work = self._get_remaining_work()
        remaining_time = self.deadline_seconds - self.env.elapsed_seconds
        
        # If task is already completed
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Check if we can still meet the deadline
        min_time_needed = remaining_work
        if self.remaining_restart_overhead > 0:
            min_time_needed += self.overhead_seconds
        
        if remaining_time < min_time_needed:
            # Emergency mode: use on-demand if we're behind schedule
            return ClusterType.ON_DEMAND
        
        # Check if we should switch regions
        if self._should_switch_region(current_region, has_spot, time_idx):
            best_region, best_has_spot, _ = self._find_best_region(time_idx)
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, use spot if available in new region
                if best_has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        # Calculate slack time
        slack_time = remaining_time - min_time_needed
        
        # Determine strategy based on slack and current conditions
        if slack_time > 3 * self.time_step:  # Plenty of slack
            if has_spot:
                return ClusterType.SPOT
            elif slack_time > 5 * self.time_step:
                # Enough slack to wait for spot
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        elif slack_time > self.time_step:  # Moderate slack
            if has_spot:
                return ClusterType.SPOT
            else:
                # Check if spot will be available soon in current region
                future_spot = False
                lookahead = min(3, len(self.spot_availability[current_region]) - time_idx)
                for i in range(1, lookahead + 1):
                    if self.spot_availability[current_region][time_idx + i]:
                        future_spot = True
                        break
                
                if future_spot and slack_time > 2 * self.time_step:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
        
        else:  # Little to no slack
            return ClusterType.ON_DEMAND
