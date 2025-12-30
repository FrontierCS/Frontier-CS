import json
from argparse import Namespace
import math
from typing import List, Tuple
from dataclasses import dataclass

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


@dataclass
class RegionState:
    spot_history: List[bool]
    last_spot_check: float
    reliability_score: float


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_optimizer"

    def __init__(self, args):
        super().__init__(args)
        self.region_states = {}
        self.last_action = None
        self.region_history = {}
        self.spot_history_window = 10
        self.safety_margin = 1.1

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
        
        self.cost_ratio = 3.06 / 0.9701  # On-demand / Spot price ratio
        self.initial_regions = self.env.get_num_regions() if hasattr(self.env, 'get_num_regions') else 1
        
        return self

    def _update_region_state(self, region_idx: int, has_spot: bool):
        if region_idx not in self.region_states:
            self.region_states[region_idx] = RegionState(
                spot_history=[has_spot],
                last_spot_check=self.env.elapsed_seconds,
                reliability_score=1.0 if has_spot else 0.0
            )
        else:
            state = self.region_states[region_idx]
            state.spot_history.append(has_spot)
            if len(state.spot_history) > self.spot_history_window:
                state.spot_history.pop(0)
            
            # Update reliability score (exponential moving average)
            spot_availability = sum(state.spot_history) / len(state.spot_history)
            alpha = 0.3
            state.reliability_score = alpha * spot_availability + (1 - alpha) * state.reliability_score
            state.last_spot_check = self.env.elapsed_seconds

    def _get_best_alternative_region(self, current_region: int, has_spot: bool) -> Tuple[int, float]:
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_score = -float('inf')
        
        for region in range(num_regions):
            if region == current_region:
                continue
                
            if region in self.region_states:
                state = self.region_states[region]
                # Score based on reliability and recentness of info
                time_since_check = self.env.elapsed_seconds - state.last_spot_check
                recency_factor = max(0, 1.0 - time_since_check / (3600 * 4))  # 4 hour decay
                score = state.reliability_score * recency_factor
                
                if score > best_score:
                    best_score = score
                    best_region = region
            else:
                # Unknown region - assign medium score
                if 0.5 > best_score:
                    best_score = 0.5
                    best_region = region
        
        return best_region, best_score

    def _calculate_safety_buffer(self) -> float:
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        if work_remaining <= 0:
            return float('inf')
        
        # Minimum time needed if we use only on-demand
        min_time_needed = work_remaining
        
        # Estimate with potential overheads
        estimated_overheads = self.restart_overhead * 2  # Conservative estimate
        estimated_time_needed = work_remaining + estimated_overheads
        
        safety_buffer = (time_remaining - estimated_time_needed) / self.env.gap_seconds
        return safety_buffer

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        
        # Update region state
        self._update_region_state(current_region, has_spot)
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # If work is done, stop
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If we can't possibly finish, use on-demand
        min_time_needed = work_remaining
        if time_remaining < min_time_needed:
            return ClusterType.ON_DEMAND
        
        # Calculate safety buffer (in number of steps)
        safety_buffer = self._calculate_safety_buffer()
        
        # If we're in critical zone, use on-demand
        if safety_buffer < 2:  # Less than 2 steps of buffer
            return ClusterType.ON_DEMAND
        
        # Check if we should switch regions for better spot availability
        if not has_spot and safety_buffer > 4:  # Only switch if we have buffer
            best_alt_region, alt_score = self._get_best_alternative_region(current_region, has_spot)
            
            if alt_score > 0.3 and best_alt_region != current_region:
                # Switch region if alternative looks promising
                self.env.switch_region(best_alt_region)
                # After switching, check spot availability in new region
                # We'll use the reliability score to decide
                if alt_score > 0.7:
                    return ClusterType.SPOT
                else:
                    # Conservative: use on-demand first in new region
                    return ClusterType.ON_DEMAND
        
        # Main decision logic
        if has_spot:
            # Use spot if we have sufficient safety buffer
            if safety_buffer > 3:  # Good buffer
                return ClusterType.SPOT
            elif safety_buffer > 1.5:  # Moderate buffer
                # Mix strategy: use spot 70% of time conceptually
                # Simple implementation: check elapsed time
                cycle = int(self.env.elapsed_seconds / self.env.gap_seconds) % 10
                if cycle < 7:  # 70% spot usage
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if safety_buffer > 5:  # Large buffer, can wait
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND