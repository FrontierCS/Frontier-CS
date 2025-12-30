import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by prioritizing
    spot instances while ensuring the task finishes before the deadline.

    The strategy operates in two main modes:
    1. Panic Mode: If the remaining time is barely enough to finish the task
       using a guaranteed On-Demand instance, it will switch to On-Demand to
       avoid failing the deadline. A safety buffer is included to handle
       unexpected delays.
    2. Opportunistic Mode: Otherwise, it seeks the cheapest execution path.
       - It evaluates all available regions based on their spot instance
         availability in a future time window (lookahead).
       - If the current region has a spot instance, it uses it unless another
         region is significantly better and has a spot instance available now.
         This prevents frequent, costly region switches ("flapping").
       - If the current region lacks a spot instance, it switches to the best
         alternative region that has a spot instance available immediately.
       - If no spot instances are available anywhere, it waits (ClusterType.NONE)
         for a spot instance to become available, as this is more cost-effective
         than using On-Demand when not in "Panic Mode".

    To achieve efficient decision-making, spot availability traces are pre-processed
    into prefix sums, allowing for constant-time calculation of spot availability
    within any future time window.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        # Custom initialization
        self.spot_traces = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as f:
                        self.spot_traces.append(json.load(f))
                except (IOError, json.JSONDecodeError):
                    # For this problem, assume files are present and valid.
                    pass
        
        self.num_regions = self.env.get_num_regions()
        
        if not self.spot_traces or not self.spot_traces[0]:
            self.trace_len = 0
            self.spot_counts = []
        else:
            # Ensure all traces are of the same length for simplicity
            self.trace_len = len(self.spot_traces[0])
            self.spot_counts = []
            for trace in self.spot_traces:
                sanitized_trace = trace[:self.trace_len]
                counts = [0] * (self.trace_len + 1)
                for i in range(self.trace_len):
                    counts[i + 1] = counts[i] + int(sanitized_trace[i])
                self.spot_counts.append(counts)
        
        # Tunable parameters for the strategy
        self.LOOKAHEAD_WINDOW = 12
        self.SWITCHING_THRESHOLD = 1
        # A safety buffer to switch to On-Demand before it's too late,
        # accounting for one lost timestep and the restart penalty.
        self.SAFETY_BUFFER = self.env.gap_seconds + self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Housekeeping: Calculate current state variables
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        current_timestep = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_region = self.env.get_current_region()

        # 2. Panic Mode: Check if we must use On-Demand to meet the deadline
        on_demand_time_needed = work_remaining + self.restart_overhead
        if time_left <= on_demand_time_needed + self.SAFETY_BUFFER:
            return ClusterType.ON_DEMAND

        # Fallback if we are past the end of our trace data
        if current_timestep >= self.trace_len:
            # No spot data. Since we are not in panic mode, it's cheapest to wait.
            return ClusterType.NONE

        # 3. Region Evaluation: Score regions based on future spot availability
        goodness = [0] * self.num_regions
        start_idx = current_timestep
        end_idx = min(current_timestep + self.LOOKAHEAD_WINDOW, self.trace_len)

        for r in range(self.num_regions):
            goodness[r] = self.spot_counts[r][end_idx] - self.spot_counts[r][start_idx]

        # 4. Decision Logic
        if has_spot:
            # We have a spot instance. Decide whether to stay or switch.
            current_goodness = goodness[current_region]
            
            best_other_region = -1
            max_other_goodness = -1
            # Find the best *other* region
            for r in range(self.num_regions):
                if r == current_region:
                    continue
                if goodness[r] > max_other_goodness:
                    max_other_goodness = goodness[r]
                    best_other_region = r
            
            # Switch only if another region is significantly better and has spot now
            if best_other_region != -1 and \
               max_other_goodness > current_goodness + self.SWITCHING_THRESHOLD and \
               self.spot_traces[best_other_region][current_timestep]:
                self.env.switch_region(best_other_region)
                return ClusterType.SPOT

            # Otherwise, stay and use the current spot instance
            return ClusterType.SPOT
        
        else:  # not has_spot
            # No spot here. Find the best region and switch if it has spot now.
            max_goodness = -1
            best_region = -1
            if goodness:
                max_goodness = max(goodness)
                best_region = goodness.index(max_goodness)

            if best_region != -1 and max_goodness > 0 and self.spot_traces[best_region][current_timestep]:
                if best_region != current_region:
                    self.env.switch_region(best_region)
                return ClusterType.SPOT
            
            # If no promising region has spot available right now, wait.
            return ClusterType.NONE