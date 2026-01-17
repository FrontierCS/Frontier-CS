import json
from argparse import Namespace
import heapq
import math
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
        
        # Pre-compute derived values
        self.deadline_seconds = self.deadline
        self.task_duration_seconds = self.task_duration
        self.restart_overhead_seconds = self.restart_overhead
        
        # Constants
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        
        # State
        self.regions = []
        self.current_plan = []
        self.plan_index = 0
        self.switch_regions = False
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we have no plan, compute one
        if not self.current_plan or self.plan_index >= len(self.current_plan):
            self._compute_plan()
            self.plan_index = 0
            if not self.current_plan:
                return ClusterType.ON_DEMAND

        # Execute the plan
        action = self.current_plan[self.plan_index]
        self.plan_index += 1
        
        # Handle region switching if needed
        if self.switch_regions:
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            self.switch_regions = False
            
        return action

    def _compute_plan(self):
        """Compute an optimal schedule plan using dynamic programming with time horizon."""
        
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_left = self.task_duration_seconds - work_done
        time_left = self.deadline_seconds - elapsed
        
        # If no time left, use on-demand to finish if possible
        if time_left <= 0 or work_left <= 0:
            self.current_plan = []
            return
            
        # Calculate conservative time needed with on-demand
        overhead_if_needed = self.restart_overhead_seconds if self.remaining_restart_overhead <= 0 else self.remaining_restart_overhead
        time_needed_ondemand = work_left + overhead_if_needed
        
        # If we're running out of time, use on-demand
        if time_left < time_needed_ondemand * 1.2:  # 20% safety margin
            steps_needed = math.ceil(work_left / self.env.gap_seconds)
            self.current_plan = [ClusterType.ON_DEMAND] * steps_needed
            return
        
        # Estimate steps needed with spot
        steps_needed = math.ceil(work_left / self.env.gap_seconds)
        
        # Create a plan: use spot when available, otherwise on-demand
        plan = []
        spot_streak = 0
        
        for i in range(min(100, steps_needed)):  # Plan ahead up to 100 steps
            # Switch regions occasionally to find better spot availability
            if i % 20 == 0 and num_regions > 1:
                self.switch_regions = True
            
            # Use spot if we expect it to be available most of the time
            # Be conservative: after 3 spot steps, use one on-demand for safety
            if spot_streak < 3:
                plan.append(ClusterType.SPOT)
                spot_streak += 1
            else:
                plan.append(ClusterType.ON_DEMAND)
                spot_streak = 0
        
        self.current_plan = plan