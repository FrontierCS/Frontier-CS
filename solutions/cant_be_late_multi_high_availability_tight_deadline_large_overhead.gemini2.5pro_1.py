import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that minimizes cost by prioritizing spot instances
    while ensuring the task completes before the deadline.

    The strategy is based on the following principles:
    1.  Pre-computation: In the `solve` method, it loads all spot availability traces
        and pre-computes the length of consecutive future spot availability for every
        region and timestep. This allows for fast, informed decisions in the `_step` method.
    2.  Deadline-Awareness ("Panic Mode"): The highest priority is to not miss the
        deadline. At each step, it calculates the time required to finish the remaining
        work using a reliable on-demand instance. If this projected finish time is too
        close to the deadline, it switches to on-demand to guarantee completion.
    3.  Greedy Spot Exploitation: To minimize cost, it aggressively uses spot instances.
        - If the current region has spot availability, it uses it immediately. This avoids
          the time cost of switching regions and makes cheap progress.
        - If the current region lacks spot, it searches for an alternative region that
          has spot available *at the current timestep*. Among those, it picks the one
          with the longest pre-computed future availability.
    4.  Strategic Waiting: If no spot instances are available in any region, the strategy
        evaluates if it can afford to wait. It calculates its "slack time" (the buffer
        before the deadline-driven "panic mode" would be triggered). If there is enough
        slack, it chooses to wait (ClusterType.NONE), saving money and hoping for spot
        availability in the next step. Otherwise, it uses on-demand to ensure progress.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config. This method loads the
        problem specification and pre-computes spot availability data for
        efficient decision-making in the _step method.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        
        trace_files = config.get("trace_files", [])
        # Pass trace_files to the super constructor, which may use them to init the environment
        super().__init__(args, trace_files=trace_files)

        # Load trace data for our own strategy's use
        self.spot_availability = []
        for trace_file in trace_files:
            with open(trace_file, 'r') as f:
                self.spot_availability.append([bool(int(line.strip())) for line in f.readlines()])

        self.num_regions = len(self.spot_availability)
        if self.num_regions > 0:
            self.num_timesteps = len(self.spot_availability[0])
        else:
            self.num_timesteps = 0

        # Pre-calculate, for each (region, timestep), the length of the
        # consecutive run of spot availability starting from that point.
        self.future_spot_runs = [[0] * self.num_timesteps for _ in range(self.num_regions)]
        if self.num_timesteps > 0:
            for r in range(self.num_regions):
                count = 0
                for t in range(self.num_timesteps - 1, -1, -1):
                    if self.spot_availability[r][t]:
                        count += 1
                    else:
                        count = 0
                    self.future_spot_runs[r][t] = count
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action (SPOT, ON_DEMAND, or NONE) based on the current state
        and pre-computed trace data.
        """
        # 1. Calculate current state
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If task is complete, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        current_timestep = int(self.env.elapsed_seconds / self.env.gap_seconds)
        
        # Time needed to finish if we start ON_DEMAND now (worst-case, with a restart)
        time_needed_for_od = work_remaining + self.restart_overhead

        # Handle the edge case where the simulation runs longer than the provided trace data.
        if current_timestep >= self.num_timesteps:
            # Assume no spot availability. Decide between ON_DEMAND and NONE.
            time_needed_for_od_fallback = work_remaining
            if last_cluster_type != ClusterType.ON_DEMAND:
                time_needed_for_od_fallback += self.restart_overhead
            
            # Check if we can afford to wait one more step.
            time_if_wait_one_step = self.env.elapsed_seconds + self.env.gap_seconds + time_needed_for_od_fallback
            if self.deadline - time_if_wait_one_step > 0:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

        # 2. "Panic Mode": Use ON_DEMAND if the deadline is at risk.
        projected_finish_time = self.env.elapsed_seconds + time_needed_for_od
        if projected_finish_time >= self.deadline:
            # Must use on-demand. Do not switch regions to avoid any further overhead.
            return ClusterType.ON_DEMAND

        # 3. Greedy Strategy: Prioritize using SPOT in the current region if available.
        if has_spot:
            return ClusterType.SPOT

        # 4. Search: Current region has no spot. Find the best alternative region with spot available *now*.
        best_alt_region = -1
        max_future_run = -1
        for r in range(self.num_regions):
            if self.spot_availability[r][current_timestep]:
                # This region has spot now. Check its future prospects.
                future_run = self.future_spot_runs[r][current_timestep]
                if future_run > max_future_run:
                    max_future_run = future_run
                    best_alt_region = r

        # If we found a viable alternative region, switch to it and use SPOT.
        if best_alt_region != -1:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        # 5. Wait or Act: No region has spot available right now. Decide between waiting (NONE) or using ON_DEMAND.
        time_if_wait_one_step = self.env.elapsed_seconds + self.env.gap_seconds + time_needed_for_od
        slack_if_wait = self.deadline - time_if_wait_one_step

        if slack_if_wait > 0:
            # We have slack to wait for at least one step.
            return ClusterType.NONE
        else:
            # Not enough slack. We must make progress using ON_DEMAND.
            return ClusterType.ON_DEMAND
