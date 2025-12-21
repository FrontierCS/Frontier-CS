import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "efficient_scheduler"

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
        
        # Store config for reference
        self.config = config
        self.trace_files = config.get("trace_files", [])
        self.num_regions = len(self.trace_files)
        
        # Preprocess traces
        self.traces = []
        self.spot_availability = []
        self.spot_windows = []
        
        for trace_file in self.trace_files:
            with open(trace_file, 'r') as f:
                trace_data = [int(line.strip()) for line in f]
                self.traces.append(trace_data)
                self.spot_availability.append(trace_data)
                
                # Precompute spot availability windows
                windows = []
                in_window = False
                start = 0
                for i, available in enumerate(trace_data):
                    if available and not in_window:
                        start = i
                        in_window = True
                    elif not available and in_window:
                        windows.append((start, i-1))
                        in_window = False
                if in_window:
                    windows.append((start, len(trace_data)-1))
                self.spot_windows.append(windows)
        
        # Prices
        self.spot_price = 0.9701  # $/hr
        self.on_demand_price = 3.06  # $/hr
        
        # Planning
        self.plan = []
        self.current_plan_index = 0
        self.backup_plan = []
        
        return self

    def _precompute_plan(self) -> None:
        """Precompute an optimal plan using dynamic programming."""
        gap_hours = self.env.gap_seconds / 3600.0
        total_steps = int(math.ceil(self.deadline / self.env.gap_seconds))
        task_duration_hours = self.task_duration / 3600.0
        restart_hours = self.restart_overhead / 3600.0
        
        # Convert traces to hours
        hours_per_step = gap_hours
        max_hours = self.deadline / 3600.0
        
        # Initialize DP table
        # dp[region][time][work_done] = min_cost
        # We'll use a more efficient representation
        dp_regions = self.num_regions
        dp_time_slots = total_steps + 1
        work_slots = int(math.ceil(task_duration_hours / hours_per_step)) + 1
        
        # Use A* search instead of full DP
        self._build_a_star_plan()
    
    def _build_a_star_plan(self) -> None:
        """Build plan using heuristic A* search."""
        gap_hours = self.env.gap_seconds / 3600.0
        total_steps = int(math.ceil(self.deadline / self.env.gap_seconds))
        task_duration_hours = self.task_duration / 3600.0
        restart_hours = self.restart_overhead / 3600.0
        
        # State: (time_step, work_done, region, has_overhead, cost)
        # We'll use priority queue with heuristic
        heap = []
        
        # Heuristic: optimistic remaining cost if all work done with spot
        def heuristic(state):
            time_step, work_done, region, has_overhead, cost = state
            remaining_work = task_duration_hours - work_done
            optimistic_cost = cost + remaining_work * self.spot_price
            # Penalize if we're running out of time
            remaining_time = (total_steps - time_step) * gap_hours
            if remaining_work > remaining_time:
                optimistic_cost += 100000  # High penalty for missing deadline
            return optimistic_cost
        
        # Initial state
        init_state = (0, 0.0, 0, False, 0.0)
        heapq.heappush(heap, (heuristic(init_state), init_state))
        
        # Visited states
        visited = {}
        
        # Backtracking info
        backtrack = {}
        
        best_state = None
        best_cost = float('inf')
        
        while heap:
            _, state = heapq.heappop(heap)
            time_step, work_done, region, has_overhead, cost = state
            
            # Check if we've visited this state with lower cost
            key = (time_step, round(work_done, 4), region, has_overhead)
            if key in visited and visited[key] <= cost:
                continue
            visited[key] = cost
            
            # Check if we're done
            if work_done >= task_duration_hours:
                if cost < best_cost:
                    best_cost = cost
                    best_state = state
                continue
            
            # Check if we're out of time
            if time_step >= total_steps:
                continue
            
            # Generate next states
            current_spot_available = self.spot_availability[region][time_step] if time_step < len(self.spot_availability[region]) else 0
            
            # Action 1: Use spot if available
            if current_spot_available:
                new_work = work_done + gap_hours
                new_cost = cost + gap_hours * self.spot_price
                # No overhead if we were already running or if we're starting fresh
                new_overhead = False
                new_state = (time_step + 1, new_work, region, new_overhead, new_cost)
                heapq.heappush(heap, (heuristic(new_state), new_state))
                backtrack[new_state] = (state, 'spot', region)
            
            # Action 2: Use on-demand
            new_work = work_done + gap_hours
            new_cost = cost + gap_hours * self.on_demand_price
            new_overhead = False
            new_state = (time_step + 1, new_work, region, new_overhead, new_cost)
            heapq.heappush(heap, (heuristic(new_state), new_state))
            backtrack[new_state] = (state, 'on_demand', region)
            
            # Action 3: Switch region (if there are other regions)
            for new_region in range(self.num_regions):
                if new_region == region:
                    continue
                # Switching incurs overhead (loses current timestep)
                new_time = time_step + 1
                # Check if spot available in new region at next timestep
                next_spot = self.spot_availability[new_region][new_time] if new_time < len(self.spot_availability[new_region]) else 0
                
                if next_spot:
                    # We'll start with spot in next timestep
                    new_work = work_done
                    new_cost = cost  # No additional cost for switch, just lost time
                    new_overhead = True
                    new_state = (new_time, new_work, new_region, new_overhead, new_cost)
                    heapq.heappush(heap, (heuristic(new_state), new_state))
                    backtrack[new_state] = (state, 'switch', new_region)
            
            # Action 4: Do nothing (pause)
            new_state = (time_step + 1, work_done, region, False, cost)
            heapq.heappush(heap, (heuristic(new_state), new_state))
            backtrack[new_state] = (state, 'none', region)
        
        # Reconstruct plan if we found a solution
        if best_state:
            plan = []
            state = best_state
            while state in backtrack:
                prev_state, action, region = backtrack[state]
                plan.append((action, region))
                state = prev_state
            plan.reverse()
            self.plan = plan
        else:
            # Fallback: simple greedy plan
            self._build_greedy_plan()
    
    def _build_greedy_plan(self) -> None:
        """Build a simple greedy plan as fallback."""
        gap_hours = self.env.gap_seconds / 3600.0
        total_steps = int(math.ceil(self.deadline / self.env.gap_seconds))
        task_duration_hours = self.task_duration / 3600.0
        
        plan = []
        current_region = 0
        work_done = 0.0
        
        for step in range(total_steps):
            if work_done >= task_duration_hours:
                plan.append(('none', current_region))
                continue
            
            # Check spot availability in current region
            spot_available = self.spot_availability[current_region][step] if step < len(self.spot_availability[current_region]) else 0
            
            # Check if we should switch to a region with spot available
            best_region = current_region
            best_spot = spot_available
            
            for region in range(self.num_regions):
                if region == current_region:
                    continue
                future_spot = self.spot_availability[region][step] if step < len(self.spot_availability[region]) else 0
                if future_spot > best_spot:
                    best_spot = future_spot
                    best_region = region
            
            if best_region != current_region and best_spot:
                plan.append(('switch', best_region))
                current_region = best_region
                spot_available = best_spot
            elif spot_available:
                plan.append(('spot', current_region))
                work_done += gap_hours
            else:
                # Check if we have enough time to wait for spot
                remaining_time = (total_steps - step - 1) * gap_hours
                remaining_work = task_duration_hours - work_done
                
                if remaining_work <= remaining_time - gap_hours:  # Can afford to wait
                    # Look ahead for spot availability
                    found_spot = False
                    for lookahead in range(1, min(6, total_steps - step)):  # Look ahead up to 6 steps
                        future_spot = self.spot_availability[current_region][step + lookahead] if (step + lookahead) < len(self.spot_availability[current_region]) else 0
                        if future_spot:
                            plan.append(('none', current_region))
                            found_spot = True
                            break
                    
                    if not found_spot:
                        # Switch to any region with spot
                        for region in range(self.num_regions):
                            if region == current_region:
                                continue
                            future_spot = self.spot_availability[region][step] if step < len(self.spot_availability[region]) else 0
                            if future_spot:
                                plan.append(('switch', region))
                                current_region = region
                                spot_available = True
                                break
                        if not spot_available:
                            plan.append(('on_demand', current_region))
                            work_done += gap_hours
                else:
                    # Running out of time, use on-demand
                    plan.append(('on_demand', current_region))
                    work_done += gap_hours
        
        self.plan = plan
    
    def _get_emergency_plan(self) -> Tuple[str, int]:
        """Get emergency plan when running out of time."""
        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If we're critically behind, use on-demand
        if remaining_work > remaining_time - self.restart_overhead:
            return 'on_demand', self.env.get_current_region()
        
        # Otherwise try to find spot
        current_region = self.env.get_current_region()
        spot_available = self.spot_availability[current_region][current_step] if current_step < len(self.spot_availability[current_region]) else 0
        
        if spot_available:
            return 'spot', current_region
        
        # Check other regions
        for region in range(self.num_regions):
            if region == current_region:
                continue
            spot = self.spot_availability[region][current_step] if current_step < len(self.spot_availability[region]) else 0
            if spot:
                return 'switch', region
        
        # Default to on-demand
        return 'on_demand', current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate current progress
        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # Emergency check: if we're running out of time
        if remaining_work > remaining_time - self.restart_overhead:
            action, region = self._get_emergency_plan()
        else:
            # Use precomputed plan if available
            if hasattr(self, 'plan') and current_step < len(self.plan):
                action, region = self.plan[current_step]
            else:
                # Generate plan on the fly
                if not hasattr(self, 'plan'):
                    self._build_greedy_plan()
                if current_step < len(self.plan):
                    action, region = self.plan[current_step]
                else:
                    action, region = self._get_emergency_plan()
        
        # Execute action
        if action == 'switch':
            self.env.switch_region(region)
            # After switch, check if spot is available in new region
            new_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
            new_region = self.env.get_current_region()
            spot_available = self.spot_availability[new_region][new_step] if new_step < len(self.spot_availability[new_region]) else 0
            if spot_available:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        elif action == 'spot':
            if has_spot:
                return ClusterType.SPOT
            else:
                # Spot not available as expected, fallback to on-demand
                return ClusterType.ON_DEMAND
        elif action == 'on_demand':
            return ClusterType.ON_DEMAND
        else:  # 'none'
            return ClusterType.NONE
