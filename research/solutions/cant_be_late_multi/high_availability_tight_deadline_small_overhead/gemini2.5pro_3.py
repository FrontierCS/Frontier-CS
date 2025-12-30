import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "expert_scheduler"  # REQUIRED: unique identifier

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
            # Pass trace_files to the base class, which might use it
            trace_files=config.get("trace_files", [])
        )
        super().__init__(args)

        # Load and process traces for our own logic
        self.all_traces = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file, 'r') as f:
                        # Assuming a simple format: one number (0 or 1) per line
                        trace = [bool(int(line.strip())) for line in f if line.strip()]
                    self.all_traces.append(np.array(trace, dtype=bool))
                except (IOError, ValueError):
                    # Handle cases where a trace file might be empty or invalid
                    self.all_traces.append(np.array([], dtype=bool))
        
        num_regions = len(self.all_traces)
        if num_regions == 0:
            self.region_quality = []
            # Set a default threshold: wait only if slack > one restart overhead
            self.wait_slack_threshold = self.restart_overhead + 1.0
            return self

        # Pre-compute statistics from traces
        self.spot_availability_rates = []
        for trace in self.all_traces:
            if trace.size > 0:
                self.spot_availability_rates.append(np.mean(trace))
            else:
                self.spot_availability_rates.append(0.0)
        self.region_quality = np.argsort(self.spot_availability_rates)[::-1].tolist()

        # Calculate average downtime for a more informed waiting strategy
        total_downtime_steps = 0
        total_downtime_periods = 0
        for r in range(num_regions):
            trace = self.all_traces[r]
            if trace.size == 0 or not np.any(~trace): # No downtime if all available
                 continue

            in_downtime = False
            current_downtime = 0
            for available in trace:
                if not available:
                    if not in_downtime:
                        in_downtime = True
                        total_downtime_periods += 1
                    current_downtime += 1
                elif in_downtime:
                    in_downtime = False
                    total_downtime_steps += current_downtime
                    current_downtime = 0
            if in_downtime:
                total_downtime_steps += current_downtime

        if total_downtime_periods > 0:
            avg_global_downtime_steps = total_downtime_steps / total_downtime_periods
        else:
            avg_global_downtime_steps = 0

        avg_global_downtime_s = avg_global_downtime_steps * self.env.gap_seconds
        
        # Threshold for waiting: wait if slack > avg downtime + one safety restart overhead
        self.wait_slack_threshold = avg_global_downtime_s + self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        progress = sum(self.task_done_time)
        work_rem = self.task_duration - progress

        # 1. Termination condition: If the task is done, do nothing.
        if work_rem <= 0:
            return ClusterType.NONE

        t = self.elapsed_seconds
        time_left = self.deadline - t
        slack = time_left - work_rem

        # 2. Criticality Check (Danger Zone):
        # If time left is less than work remaining plus a safety buffer for one
        # potential preemption, we must use the reliable On-Demand instance.
        if time_left <= work_rem + self.restart_overhead:
            return ClusterType.ON_DEMAND

        # 3. Preferred Case: Spot is available in the current region.
        if has_spot:
            return ClusterType.SPOT

        # 4. No Spot Locally: Search for Spot in other regions.
        # This is only advisable if it's safe to incur the restart overhead
        # from switching regions. We check if we have enough slack for both
        # the switch and a potential future preemption.
        is_safe_to_switch = (slack > 2 * self.restart_overhead)
        if is_safe_to_switch and self.all_traces:
            timestep = int(round(t / self.env.gap_seconds))
            current_region = self.env.get_current_region()

            # Iterate through regions, from best to worst availability
            for region_idx in self.region_quality:
                if region_idx == current_region:
                    continue
                
                trace = self.all_traces[region_idx]
                if timestep < trace.size and trace[timestep]:
                    self.env.switch_region(region_idx)
                    return ClusterType.SPOT

        # 5. No Spot Anywhere (or Unsafe to Switch):
        # Decide between waiting (NONE) and using On-Demand locally.
        if slack > self.wait_slack_threshold:
            # We have enough slack to wait for Spot to (hopefully) reappear.
            return ClusterType.NONE
        else:
            # Slack is low; we must make progress now to avoid future risk.
            return ClusterType.ON_DEMAND