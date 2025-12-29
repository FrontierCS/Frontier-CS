import json
import os
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "ClairvoyantScheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-compute spot data.
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

        self.work_done_seconds = 0.0
        self.last_task_done_time_len = 0
        
        self.has_perfect_info = False
        self.spot_streaks = []

        try:
            spec_dir = os.path.dirname(os.path.abspath(spec_path))
            trace_files = config.get("trace_files", [])
            if not trace_files:
                return self
                
            spot_traces = []
            for trace_file in trace_files:
                full_path = os.path.join(spec_dir, trace_file)
                if not os.path.exists(full_path):
                    self.has_perfect_info = False
                    self.spot_streaks = []
                    return self
                with open(full_path, 'r') as f:
                    trace_data = json.load(f)
                    spot_traces.append([bool(x) for x in trace_data])

            if not spot_traces:
                return self

            num_timesteps = len(spot_traces[0])
            for trace in spot_traces:
                if len(trace) != num_timesteps:
                    self.has_perfect_info = False
                    self.spot_streaks = []
                    return self
            
            for trace in spot_traces:
                streaks = [0] * num_timesteps
                current_streak = 0
                for i in range(num_timesteps - 1, -1, -1):
                    if trace[i]:
                        current_streak += 1
                    else:
                        current_streak = 0
                    streaks[i] = current_streak
                self.spot_streaks.append(streaks)
            
            self.has_perfect_info = True

        except (IOError, json.JSONDecodeError, KeyError, IndexError):
            self.has_perfect_info = False
            self.spot_streaks = []
            
        return self

    def _update_work_done(self):
        """Efficiently update the total work done."""
        if len(self.task_done_time) > self.last_task_done_time_len:
            self.work_done_seconds += sum(self.task_done_time[self.last_task_done_time_len:])
            self.last_task_done_time_len = len(self.task_done_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and pre-computed spot data.
        """
        self._update_work_done()
        work_remaining = self.task_duration - self.work_done_seconds

        if work_remaining <= 0:
            return ClusterType.NONE

        if (self.env.elapsed_seconds + work_remaining + self.restart_overhead >= self.deadline):
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self.has_perfect_info:
            current_timestep = int(self.env.elapsed_seconds / self.env.gap_seconds)
            
            best_region_idx = -1
            max_streak = 0

            num_regions = self.env.get_num_regions()
            if num_regions == len(self.spot_streaks):
                for r_idx in range(num_regions):
                    if current_timestep < len(self.spot_streaks[r_idx]):
                        streak = self.spot_streaks[r_idx][current_timestep]
                        if streak > max_streak:
                            max_streak = streak
                            best_region_idx = r_idx
                
                if best_region_idx != -1 and max_streak * self.env.gap_seconds > self.restart_overhead:
                    if self.env.get_current_region() != best_region_idx:
                        self.env.switch_region(best_region_idx)
                    return ClusterType.SPOT

        slack = self.deadline - (self.env.elapsed_seconds + work_remaining + self.restart_overhead)

        if slack > self.env.gap_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND