import json
from argparse import Namespace
from typing import List, Tuple
import heapq
from collections import defaultdict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_multi_region"

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
        
        # Load trace data to understand spot availability patterns
        self.trace_files = config.get("trace_files", [])
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.price_ratio = self.ondemand_price / self.spot_price
        
        # State tracking
        self.region_history = defaultdict(list)
        self.spot_availability_stats = defaultdict(list)
        self.current_plan = []
        self.replan_counter = 0
        self.last_decision = ClusterType.NONE
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # If we're done, do nothing
        if sum(self.task_done_time) >= self.task_duration:
            return ClusterType.NONE
        
        # If we have pending restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Calculate remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Convert to hours for easier calculations
        remaining_work_hours = remaining_work / 3600
        remaining_time_hours = remaining_time / 3600
        
        # Calculate critical ratio
        time_criticality = remaining_work_hours / remaining_time_hours if remaining_time_hours > 0 else float('inf')
        
        # Get current region and explore options
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Record spot availability for current region
        self.spot_availability_stats[current_region].append(has_spot)
        
        # Replan periodically or when situation changes significantly
        should_replan = (self.replan_counter % 5 == 0 or 
                        len(self.current_plan) == 0 or
                        time_criticality > 1.5 or
                        (last_cluster_type == ClusterType.SPOT and not has_spot))
        
        if should_replan:
            self.current_plan = self._create_plan(
                current_region, remaining_work_hours, remaining_time_hours
            )
            self.replan_counter = 0
        
        self.replan_counter += 1
        
        # Execute plan if we have one
        if self.current_plan:
            action = self.current_plan.pop(0)
            
            # If action requires switching region
            if action[0] != current_region:
                self.env.switch_region(action[0])
            
            # If spot is requested but not available, fall back to on-demand
            if action[1] == ClusterType.SPOT and not has_spot:
                # Update plan to reflect this change
                if self.current_plan:
                    self.current_plan[0] = (action[0], ClusterType.ON_DEMAND)
                return ClusterType.ON_DEMAND
            
            self.last_decision = action[1]
            return action[1]
        
        # Fallback heuristic if no plan
        return self._fallback_heuristic(has_spot, time_criticality)

    def _create_plan(self, current_region: int, remaining_work: float, 
                    remaining_time: float) -> List[Tuple[int, ClusterType]]:
        """
        Create a multi-step plan to minimize cost while meeting deadline.
        """
        num_regions = self.env.get_num_regions()
        plans = []
        
        # Consider staying in current region and switching to each other region
        for start_region in range(num_regions):
            # Skip if we need to switch immediately and don't have time
            if start_region != current_region and remaining_time < 0.05:
                continue
            
            plan, cost = self._plan_for_region(start_region, remaining_work, 
                                              remaining_time, start_region != current_region)
            if plan:
                plans.append((cost, plan))
        
        if not plans:
            return []
        
        # Return the cheapest feasible plan
        plans.sort(key=lambda x: x[0])
        return plans[0][1]

    def _plan_for_region(self, region: int, remaining_work: float, 
                        remaining_time: float, needs_switch: bool) -> Tuple[List[Tuple[int, ClusterType]], float]:
        """
        Create a plan for a specific starting region.
        Uses a modified knapsack approach with spot price optimization.
        """
        # Simple heuristic: use spot when available, on-demand when not
        # but switch to on-demand if we're running out of time
        plan = []
        total_cost = 0
        work_done = 0
        time_used = 0
        
        # Account for switch overhead if needed
        if needs_switch:
            time_used += self.restart_overhead / 3600  # Convert to hours
            if time_used > remaining_time:
                return [], float('inf')
        
        # Estimate spot availability in this region (simple moving average)
        spot_history = self.spot_availability_stats.get(region, [True])
        spot_probability = sum(spot_history) / max(1, len(spot_history))
        
        # Calculate how many hours we can afford to wait for spot
        safety_margin = 0.1 * remaining_time  # 10% safety margin
        max_wait_time = remaining_time - remaining_work - safety_margin
        
        # Generate plan
        while work_done < remaining_work and time_used < remaining_time:
            time_left = remaining_time - time_used
            work_needed = remaining_work - work_done
            
            # If we're very tight on time, use on-demand
            if time_left < work_needed + 0.05:  # Include overhead buffer
                plan.append((region, ClusterType.ON_DEMAND))
                total_cost += self.ondemand_price
                work_done += 1
                time_used += 1
            
            # If spot is likely available based on history, try spot
            elif spot_probability > 0.7 or max_wait_time > 2:
                plan.append((region, ClusterType.SPOT))
                total_cost += self.spot_price
                work_done += 1
                time_used += 1
                
                # If spot fails, we'll need to retry with on-demand
                # This is accounted for in the step execution
            
            # Otherwise use on-demand
            else:
                plan.append((region, ClusterType.ON_DEMAND))
                total_cost += self.ondemand_price
                work_done += 1
                time_used += 1
        
        # Check if plan is feasible
        if work_done >= remaining_work and time_used <= remaining_time:
            return plan, total_cost
        else:
            return [], float('inf')

    def _fallback_heuristic(self, has_spot: bool, time_criticality: float) -> ClusterType:
        """
        Fallback decision when no plan is available.
        """
        # If time is very critical, use on-demand
        if time_criticality > 0.9:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we're not in critical state, use it
        if has_spot and time_criticality < 0.7:
            return ClusterType.SPOT
        
        # If no spot but we can wait, pause
        if time_criticality < 0.5:
            return ClusterType.NONE
        
        # Otherwise use on-demand
        return ClusterType.ON_DEMAND