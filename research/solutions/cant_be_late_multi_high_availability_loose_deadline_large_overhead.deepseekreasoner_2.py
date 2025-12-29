import json
from argparse import Namespace
from typing import List, Dict, Tuple
import numpy as np
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
        
        # Initialize strategy state
        self.work_done = 0.0
        self.time_elapsed = 0.0
        self.last_action = ClusterType.NONE
        self.current_region = 0
        self.region_history = {}
        self.spot_predictions = {}
        self.region_costs = {}
        self.step_count = 0
        self.max_regions = 0
        self.consecutive_failures = 0
        self.safety_margin = 3600.0  # 1 hour safety margin
        
        return self

    def _update_state(self):
        """Update internal state from environment."""
        self.work_done = sum(self.task_done_time)
        self.time_elapsed = self.env.elapsed_seconds
        self.current_region = self.env.get_current_region()
        
        # Initialize region data structures
        if self.max_regions == 0:
            self.max_regions = self.env.get_num_regions()
            for i in range(self.max_regions):
                self.region_history[i] = {'spot_available': [], 'work_done': 0}
                self.spot_predictions[i] = 1.0  # Start optimistic
                self.region_costs[i] = 0.0

    def _predict_spot_availability(self, region: int, steps_ahead: int = 1) -> float:
        """Predict spot availability for a region."""
        if region not in self.region_history:
            return 1.0
        
        history = self.region_history[region]['spot_available']
        if len(history) < 10:
            return 0.7  # Default optimistic prediction
            
        # Simple moving average with decay for recent observations
        recent_weight = 0.6
        if len(history) > 20:
            recent = history[-20:]
        else:
            recent = history
            
        recent_avg = sum(recent) / len(recent)
        
        # Apply exponential smoothing
        self.spot_predictions[region] = (
            recent_weight * recent_avg + 
            (1 - recent_weight) * self.spot_predictions[region]
        )
        
        return self.spot_predictions[region]

    def _calculate_urgency(self) -> float:
        """Calculate urgency level (0-1) based on remaining time."""
        remaining_work = self.task_duration - self.work_done
        remaining_time = self.deadline - self.time_elapsed - self.safety_margin
        
        if remaining_time <= 0:
            return 1.0
            
        # Minimum time needed if we use only on-demand
        min_time_needed = remaining_work + self.restart_overhead
        
        if min_time_needed <= 0:
            return 0.0
            
        urgency = min_time_needed / remaining_time
        return min(max(urgency, 0.0), 1.0)

    def _find_best_region(self, has_spot: bool) -> Tuple[int, float]:
        """Find the best region to switch to."""
        best_region = self.current_region
        best_score = -float('inf')
        
        current_spot_pred = self._predict_spot_availability(self.current_region)
        
        for region in range(self.max_regions):
            if region == self.current_region:
                # Staying in current region has no switching cost
                spot_pred = current_spot_pred if has_spot else 0.0
                score = spot_pred * 0.9701  # Spot price
                if score > best_score:
                    best_score = score
                    best_region = region
                continue
                
            # Switching region prediction
            spot_pred = self._predict_spot_availability(region)
            
            # Calculate expected cost
            if spot_pred > 0.8:  # High confidence in spot
                expected_cost = spot_pred * 0.9701 + (1 - spot_pred) * 3.06
            else:
                expected_cost = 3.06  # Conservative
                
            # Penalize switching based on urgency
            urgency = self._calculate_urgency()
            switch_penalty = urgency * 0.5
            
            score = -expected_cost - switch_penalty
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region, best_score

    def _should_switch_to_ondemand(self, has_spot: bool) -> bool:
        """Determine if we should switch to on-demand."""
        urgency = self._calculate_urgency()
        
        # If urgency is high, use on-demand
        if urgency > 0.8:
            return True
            
        # If we've had too many consecutive spot failures
        if self.consecutive_failures > 3:
            return True
            
        # If spot prediction is low
        spot_pred = self._predict_spot_availability(self.current_region)
        if spot_pred < 0.3 and urgency > 0.3:
            return True
            
        # If we're close to deadline with significant work remaining
        remaining_work = self.task_duration - self.work_done
        remaining_time = self.deadline - self.time_elapsed
        
        if remaining_time < remaining_work * 1.5:
            return True
            
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.step_count += 1
        self._update_state()
        
        # Update region history
        if self.current_region in self.region_history:
            self.region_history[self.current_region]['spot_available'].append(1 if has_spot else 0)
            # Keep history manageable
            if len(self.region_history[self.current_region]['spot_available']) > 100:
                self.region_history[self.current_region]['spot_available'].pop(0)
        
        # Update consecutive failures counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        # If we're in restart overhead, do nothing
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # If work is complete, do nothing
        if self.work_done >= self.task_duration:
            return ClusterType.NONE
        
        # Calculate remaining time and work
        remaining_work = self.task_duration - self.work_done
        remaining_time = self.deadline - self.time_elapsed
        
        # If we can't possibly finish, use on-demand as last resort
        if remaining_time < remaining_work:
            return ClusterType.ON_DEMAND
        
        # Find best region
        best_region, region_score = self._find_best_region(has_spot)
        
        # Switch region if beneficial
        if best_region != self.current_region:
            self.env.switch_region(best_region)
            self.current_region = best_region
            # After switching, we need to reconsider based on new region
            # For simplicity, we'll use conservative approach after switch
            return ClusterType.ON_DEMAND if self._should_switch_to_ondemand(has_spot) else ClusterType.SPOT
        
        # Decision logic
        if self._should_switch_to_ondemand(has_spot):
            return ClusterType.ON_DEMAND
        
        # Use spot if available
        if has_spot:
            return ClusterType.SPOT
        
        # If spot not available and we shouldn't use on-demand, pause
        return ClusterType.NONE