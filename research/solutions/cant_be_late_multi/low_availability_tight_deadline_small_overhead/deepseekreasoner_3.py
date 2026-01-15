import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType
import math


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
        self.last_action = None
        self.consecutive_spot_failures = 0
        self.spot_history = {}
        self.region_attempts = {}
        self.current_region = None
        self.work_done = 0.0
        self.time_left = None
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track current region if not already
        if self.current_region is None:
            self.current_region = self.env.get_current_region()
        
        # Update work done and time left
        self.work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - self.work_done
        self.time_left = self.deadline - self.env.elapsed_seconds
        
        # If no work left, just pause
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Initialize region tracking
        if self.current_region not in self.spot_history:
            self.spot_history[self.current_region] = []
            self.region_attempts[self.current_region] = 0
        
        # Update spot history for current region
        self.spot_history[self.current_region].append(1 if has_spot else 0)
        if len(self.spot_history[self.current_region]) > 10:
            self.spot_history[self.current_region].pop(0)
        
        # Emergency mode: must use on-demand to meet deadline
        min_steps_needed = math.ceil(remaining_work / self.env.gap_seconds)
        time_per_step = self.env.gap_seconds
        if last_cluster_type != ClusterType.ON_DEMAND:
            min_steps_needed += 1  # Add restart overhead
        
        if self.time_left < min_steps_needed * time_per_step:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand even if it causes restart
                return ClusterType.ON_DEMAND
        
        # Calculate safe threshold for using spot
        spot_success_rate = 0.0
        if self.spot_history[self.current_region]:
            spot_success_rate = sum(self.spot_history[self.current_region]) / len(self.spot_history[self.current_region])
        
        # Determine if we should try spot
        should_try_spot = False
        
        if has_spot:
            # Calculate expected time with spot vs on-demand
            spot_expected_time = remaining_work
            if last_cluster_type != ClusterType.SPOT:
                spot_expected_time += self.restart_overhead
            
            ondemand_expected_time = remaining_work
            if last_cluster_type != ClusterType.ON_DEMAND:
                ondemand_expected_time += self.restart_overhead
            
            # Factor in cost difference (spot is cheaper)
            spot_cost = (spot_expected_time / 3600) * 0.9701
            ondemand_cost = (ondemand_expected_time / 3600) * 3.06
            
            # Try spot if it's significantly cheaper and we have time buffer
            time_buffer = self.time_left - ondemand_expected_time
            safety_margin = max(self.restart_overhead * 2, 3600)  # 2 restarts or 1 hour
            
            if time_buffer > safety_margin and spot_cost < ondemand_cost * 0.8:
                should_try_spot = True
            elif time_buffer > safety_margin * 2 and spot_cost < ondemand_cost:
                should_try_spot = True
        
        # Make decision
        if should_try_spot and has_spot:
            self.consecutive_spot_failures = 0
            self.region_attempts[self.current_region] += 1
            self.last_action = ClusterType.SPOT
            return ClusterType.SPOT
        else:
            # Try to find better region if current one is bad
            if not has_spot or spot_success_rate < 0.3:
                best_region = self.current_region
                best_score = -1
                
                for region in range(self.env.get_num_regions()):
                    if region == self.current_region:
                        continue
                    
                    # Calculate score for this region
                    attempts = self.region_attempts.get(region, 0)
                    history = self.spot_history.get(region, [])
                    success_rate = sum(history) / max(len(history), 1)
                    
                    # Prefer regions we haven't tried much with good history
                    score = success_rate - (attempts * 0.1)
                    
                    if score > best_score:
                        best_score = score
                        best_region = region
                
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    self.current_region = best_region
                    # Return NONE after switching to avoid paying for restart if no spot
                    if not has_spot:
                        self.last_action = ClusterType.NONE
                        return ClusterType.NONE
            
            # Use on-demand if spot is not available or too risky
            self.consecutive_spot_failures += 1
            self.last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND