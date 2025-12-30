import json
from argparse import Namespace
from typing import List
import heapq

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
        
        # Initialize state tracking
        self.last_total_work = 0.0
        self.consecutive_failures = 0
        self.last_spot_availability = True
        self.region_spot_history = {}
        self.region_costs = {}
        self.current_step = 0
        self.region_switch_counter = 0
        self.safe_mode = False
        self.spot_success_count = 0
        self.spot_failure_count = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.current_step += 1
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Calculate current progress
        current_total_work = sum(self.task_done_time)
        work_done_this_step = current_total_work - self.last_total_work
        self.last_total_work = current_total_work
        
        # Track spot availability history
        if current_region not in self.region_spot_history:
            self.region_spot_history[current_region] = []
        self.region_spot_history[current_region].append(has_spot)
        
        # Track spot performance
        if last_cluster_type == ClusterType.SPOT:
            if work_done_this_step > 0:
                self.spot_success_count += 1
                self.consecutive_failures = 0
            else:
                self.spot_failure_count += 1
                self.consecutive_failures += 1
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_failures = 0
        
        # Calculate remaining work and time
        work_remaining = self.task_duration - current_total_work
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate safety thresholds
        time_per_work_unit = self.env.gap_seconds
        safe_threshold = time_remaining - work_remaining * time_per_work_unit
        
        # Emergency mode: if we're running out of time
        if time_remaining < work_remaining * time_per_work_unit * 1.5:
            self.safe_mode = True
        
        # If we have very little time left, use on-demand
        if time_remaining < work_remaining * time_per_work_unit * 1.2:
            return ClusterType.ON_DEMAND
        
        # If we're in safe mode or had recent failures, be conservative
        if self.safe_mode or self.consecutive_failures >= 2:
            if has_spot and safe_threshold > self.restart_overhead * 3:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Calculate spot reliability in current region
        if current_region in self.region_spot_history:
            hist = self.region_spot_history[current_region]
            if len(hist) > 10:
                spot_reliability = sum(hist[-10:]) / 10.0
            else:
                spot_reliability = sum(hist) / max(len(hist), 1)
        else:
            spot_reliability = 0.5
        
        # Decide whether to explore other regions
        should_explore = (
            self.current_step % 20 == 0 or
            (spot_reliability < 0.3 and len(self.region_spot_history.get(current_region, [])) > 5) or
            (not has_spot and self.region_switch_counter < 3)
        )
        
        if should_explore and num_regions > 1:
            # Find best region to switch to based on spot history
            best_region = current_region
            best_reliability = spot_reliability
            
            for region in range(num_regions):
                if region == current_region:
                    continue
                    
                if region in self.region_spot_history:
                    hist = self.region_spot_history[region]
                    if hist:
                        reliability = sum(hist) / len(hist)
                        if reliability > best_reliability:
                            best_reliability = reliability
                            best_region = region
            
            if best_region != current_region:
                self.env.switch_region(best_region)
                self.region_switch_counter += 1
                # After switching, use on-demand for stability
                return ClusterType.ON_DEMAND
        
        # Main decision logic
        if has_spot:
            # Calculate if we can afford spot risk
            risk_buffer = time_remaining - work_remaining * time_per_work_unit
            overhead_risk = self.restart_overhead * 2
            
            # Use spot if we have enough buffer
            if risk_buffer > overhead_risk and spot_reliability > 0.4:
                return ClusterType.SPOT
            elif risk_buffer > overhead_risk * 2:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            if safe_threshold > self.restart_overhead * 2 and num_regions > 1:
                # Try switching region
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                self.region_switch_counter += 1
                # Use on-demand after switch for stability
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND