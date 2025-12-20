import json
from argparse import Namespace
import math
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by prioritizing
    spot instances while guaranteeing task completion before the deadline.

    The strategy operates in two main modes:
    1.  **Normal Mode**: Aggressively seeks out the cheapest compute resource (Spot)
        to make progress. It leverages perfect future information from trace files
        to find the region with the most stable upcoming spot availability.
        - If the current region has a spot instance, it is used.
        - If not, it searches all other regions for the one with the longest
          continuous streak of spot availability and switches to it.
        - If no spot instances are available anywhere, it checks if it's safe to
          wait (i.e., if waiting one step would still allow finishing on time
          using On-Demand). If safe, it pauses (NONE); otherwise, it uses
          On-Demand as a fallback.

    2.  **Panic Mode**: If the projected completion time using only On-Demand
        instances from the current moment exceeds the deadline, the strategy
        switches to a conservative mode. It will use On-Demand instances
        uninterruptedly to ensure the deadline is not missed, as this is the
        most reliable way to make progress.

    This dual-mode approach ensures that the strategy is cost-effective under
    normal conditions by maximizing spot usage, but also robust and reliable
    when the deadline is approaching. Pre-computation of spot streaks in the
    `solve` method ensures that the decision-making in `_step` is extremely fast.
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

        # Pre-process spot availability traces for all regions
        self.spot_traces = []
        if "trace_files" in config and config["trace_files"]:
            for trace_file in config["trace_files"]:
                try:
                    trace = np.loadtxt(trace_file, dtype=bool)
                    self.spot_traces.append(trace)
                except IOError:
                    # Handle cases where a trace file might be missing/unreadable
                    pass

        if not self.spot_traces or len(self.spot_traces[0]) == 0:
            self.longest_streak = np.array([[]])
            return self

        # Pre-compute the length of continuous spot availability from each time step
        traces_array = np.array(self.spot_traces, dtype=int)
        num_regions, num_steps = traces_array.shape
        
        self.longest_streak = np.zeros_like(traces_array)
        if num_steps > 0:
            self.longest_streak[:, -1] = traces_array[:, -1]
            for t in range(num_steps - 2, -1, -1):
                # If spot is available at t, streak is 1 + streak at t+1
                self.longest_streak[:, t] = (self.longest_streak[:, t + 1] + 1) * traces_array[:, t]

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 1e-9:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds

        # Calculate time needed to finish if we only use On-Demand from now on.
        if gap_seconds > 0:
            n_steps_od = math.ceil(work_rem / gap_seconds)
        else:
            # Avoid division by zero, though gap_seconds should always be positive.
            n_steps_od = float('inf') if work_rem > 1e-9 else 0
        
        time_for_work_od = n_steps_od * gap_seconds

        # 1. Panic Mode Check: Is On-Demand immediately necessary?
        is_restart_if_od = (last_cluster_type != ClusterType.ON_DEMAND)
        overhead_if_od = self.restart_overhead if is_restart_if_od else 0.0
        
        finish_time_if_od_now = elapsed_seconds + overhead_if_od + time_for_work_od
        if finish_time_if_od_now > self.deadline:
            return ClusterType.ON_DEMAND

        # 2. Normal Mode: Prioritize Spot.
        if has_spot:
            return ClusterType.SPOT

        # 3. Current region has no spot. Search for a better one.
        current_step_idx = int(round(elapsed_seconds / gap_seconds))
        
        if current_step_idx >= self.longest_streak.shape[1]:
            # Past the end of trace data, fallback to On-Demand for safety.
            return ClusterType.ON_DEMAND

        streaks_now = self.longest_streak[:, current_step_idx]
        if np.any(streaks_now > 0):
            best_region = np.argmax(streaks_now)
            if self.env.get_current_region() != best_region:
                self.env.switch_region(best_region)
            return ClusterType.SPOT
        
        # 4. No spot available anywhere. Decide between waiting or using On-Demand.
        time_after_wait = elapsed_seconds + gap_seconds
        # Waiting implies the next non-NONE action will cause a restart.
        overhead_after_wait = self.restart_overhead
        
        finish_time_if_wait_one_step = time_after_wait + overhead_after_wait + time_for_work_od
        
        if finish_time_if_wait_one_step <= self.deadline:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
