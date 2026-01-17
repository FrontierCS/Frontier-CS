import json
import math
from argparse import Namespace
from enum import Enum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Action(Enum):
    NONE = 0
    SPOT = 1
    ON_DEMAND = 2
    SWITCH_SPOT = 3
    SWITCH_OD = 4


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
        
        # Read trace files to understand spot availability patterns
        self.trace_files = config.get("trace_files", [])
        self.num_regions = len(self.trace_files)
        
        # Precompute some parameters
        self.spot_price = 0.9701  # $/hr
        self.ondemand_price = 3.06  # $/hr
        self.price_ratio = self.spot_price / self.ondemand_price
        
        # For planning
        self.consecutive_spot_fails = 0
        self.consecutive_spot_success = 0
        self.last_action = Action.NONE
        self.work_accumulated = 0
        self.time_accumulated = 0
        self.efficiency_history = []
        self.window_size = 10
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate progress metrics
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE
            
        current_time = self.env.elapsed_seconds
        time_left = self.deadline - current_time
        
        # Convert to hours for calculations
        remaining_work_hours = remaining_work / 3600
        time_left_hours = time_left / 3600
        
        # Calculate minimum time needed
        overhead_hours = self.restart_overhead / 3600
        
        # Emergency mode: if we're running out of time
        if time_left_hours < remaining_work_hours * 1.5:
            # Need to guarantee progress
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Calculate efficiency metrics
        current_region = self.env.get_current_region()
        
        # Update history
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot_success += 1
            self.consecutive_spot_fails = 0
        elif last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_fails += 1
            self.consecutive_spot_success = 0
        else:
            self.consecutive_spot_success = 0
            self.consecutive_spot_fails = 0
        
        # Decision logic based on spot availability and history
        if has_spot:
            # Spot is available
            if self.consecutive_spot_fails > 2:
                # Recent failures, consider switching
                best_region = current_region
                best_score = -1
                
                for region in range(self.env.get_num_regions()):
                    if region != current_region:
                        # Simple scoring: prefer regions we haven't failed in recently
                        score = 1.0
                        if self.last_action in [Action.SWITCH_SPOT, Action.SWITCH_OD]:
                            score -= 0.3  # Penalize frequent switching
                        
                        if score > best_score:
                            best_score = score
                            best_region = region
                
                if best_region != current_region and best_score > 0.7:
                    self.env.switch_region(best_region)
                    self.last_action = Action.SWITCH_SPOT
                    return ClusterType.SPOT
            
            # Use spot in current region
            if self.consecutive_spot_success < 3 and remaining_work_hours > 5:
                # Early in spot usage or large work remaining, be cautious
                # 80% spot, 20% on-demand mix
                if self.consecutive_spot_success % 5 == 0:
                    self.last_action = Action.ON_DEMAND
                    return ClusterType.ON_DEMAND
                else:
                    self.last_action = Action.SPOT
                    return ClusterType.SPOT
            else:
                self.last_action = Action.SPOT
                return ClusterType.SPOT
        else:
            # Spot not available
            if remaining_work_hours < 2 or time_left_hours < remaining_work_hours * 2:
                # Small remaining work or tight deadline, use on-demand
                self.last_action = Action.ON_DEMAND
                return ClusterType.ON_DEMAND
            
            # Check if switching might help
            should_switch = False
            if self.consecutive_spot_fails > 1:
                # Try another region
                for region in range(self.env.get_num_regions()):
                    if region != current_region:
                        # In real scenario we don't know future availability,
                        # but we can try switching optimistically
                        should_switch = True
                        break
            
            if should_switch:
                # Try to find a region that might have spot
                next_region = (current_region + 1) % self.env.get_num_regions()
                self.env.switch_region(next_region)
                # After switching, we don't know if spot is available,
                # so use on-demand for this step to be safe
                self.last_action = Action.SWITCH_OD
                return ClusterType.ON_DEMAND
            else:
                # Use on-demand in current region
                self.last_action = Action.ON_DEMAND
                return ClusterType.ON_DEMAND