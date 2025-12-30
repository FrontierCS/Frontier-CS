import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses perfect future information
    from traces to make optimal decisions based on a cost-benefit analysis.
    """

    NAME = "cant-be-late"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy by pre-processing trace data to enable
        efficient decision-making in each step.
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

        # Problem constants from the description
        self.price_od = 3.06
        self.price_spot = 0.9701

        # Precomputation stage
        self._load_traces(config["trace_files"])
        self._compute_spot_streaks()
        
        # A cap on the search horizon to manage performance. This value is
        # chosen to balance lookahead depth with per-step computation time.
        self.horizon_cap = 250

        return self

    def _load_traces(self, trace_files: list[str]):
        """Loads all trace files into memory."""
        self.traces = []
        for trace_file in trace_files:
            with open(trace_file) as f:
                trace = [bool(int(line.strip())) for line in f]
                self.traces.append(trace)

    def _compute_spot_streaks(self):
        """
        Pre-computes a lookup table `L` where `L[r][t]` is the length of the
        consecutive spot availability streak in region `r` starting at time `t`.
        """
        if not self.traces:
            return

        num_regions = len(self.traces)
        # Pad traces to ensure they cover the entire duration up to the deadline
        num_steps = math.ceil(self.deadline / self.env.gap_seconds) + 1
        
        for i in range(len(self.traces)):
            if len(self.traces[i]) < num_steps:
                self.traces[i].extend([False] * (num_steps - len(self.traces[i])))

        self.L = [[0] * num_steps for _ in range(num_regions)]

        for r in range(num_regions):
            for t in range(num_steps - 2, -1, -1):
                if self.traces[r][t]:
                    self.L[r][t] = 1 + self.L[r][t + 1]
                else:
                    self.L[r][t] = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the next action by evaluating the best future plan.
        """
        # 1. Get current state
        elapsed_sec = self.env.elapsed_seconds
        current_step = int(elapsed_sec / self.env.gap_seconds)
        current_region = self.env.get_current_region()
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        
        if work_left <= 0:
            return ClusterType.NONE

        # 2. Panic Check: If finishing on OD is the only way, do it.
        time_left_sec = self.deadline - elapsed_sec
        time_needed_od = self.remaining_restart_overhead + work_left
        
        if time_left_sec <= time_needed_od:
            return ClusterType.ON_DEMAND

        # 3. Find Best Plan
        # The baseline plan is to use ON_DEMAND, which has a net value of 0.
        best_plan_value = 0.0
        best_plan_action = ClusterType.ON_DEMAND
        best_plan_switch_target = -1

        # Define a search horizon based on available slack time, capped for performance.
        slack_steps = math.floor((time_left_sec - time_needed_od) / self.env.gap_seconds)
        horizon = min(current_step + slack_steps + 1, len(self.traces[0]), current_step + self.horizon_cap)

        for r in range(self.env.get_num_regions()):
            t = current_step
            while t < horizon:
                L = self.L[r][t]
                if L == 0:
                    t += 1
                    continue
                
                # A. Calculate plan cost/benefit relative to the ON_DEMAND baseline.
                is_switch = (r != current_region)
                wait_time_sec = (t - current_step) * self.env.gap_seconds
                overhead_sec = self.restart_overhead if is_switch else 0.0
                
                # Cost is the opportunity cost of time spent waiting or in overhead.
                time_cost_sec = wait_time_sec + overhead_sec
                monetary_time_cost = time_cost_sec / 3600.0 * self.price_od

                # Benefit is the savings from using SPOT instead of ON_DEMAND.
                spot_run_sec = L * self.env.gap_seconds
                monetary_benefit = spot_run_sec / 3600.0 * (self.price_od - self.price_spot)
                
                net_value = monetary_benefit - monetary_time_cost
                
                # B. Check if this plan is better and feasible.
                if net_value > best_plan_value:
                    time_needed_for_plan_sec = time_cost_sec + spot_run_sec
                    work_done_by_plan = spot_run_sec
                    
                    work_left_after_plan = work_left - work_done_by_plan
                    time_at_plan_end = elapsed_sec + time_needed_for_plan_sec
                    time_left_at_plan_end = self.deadline - time_at_plan_end
                    
                    od_time_after_plan = max(0, work_left_after_plan)
                    
                    is_feasible = (time_left_at_plan_end >= od_time_after_plan)

                    if is_feasible:
                        best_plan_value = net_value
                        if t == current_step:
                            # Immediate action: use SPOT.
                            best_plan_action = ClusterType.SPOT
                            best_plan_switch_target = r if is_switch else -1
                        else:
                            # Future action: wait for now.
                            best_plan_action = ClusterType.NONE
                            best_plan_switch_target = -1
                
                # Optimization: jump to the end of the current spot block.
                t += L

        # 4. Execute the best plan found.
        if best_plan_action == ClusterType.SPOT and best_plan_switch_target != -1:
             self.env.switch_region(best_plan_switch_target)
        
        return best_plan_action