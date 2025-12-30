import json
from argparse import Namespace
import numpy as np
import pandas as pd

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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

        trace_files = config.get('trace_files', [])
        self.num_regions = len(trace_files)
        raw_traces = []
        for trace_file in trace_files:
            try:
                df = pd.read_csv(trace_file, header=None, dtype=bool)
                raw_traces.append(df.iloc[:, 0].to_numpy())
            except Exception:
                try:
                    with open(trace_file, 'r') as f_trace:
                        trace = [bool(int(line.strip())) for line in f_trace]
                    raw_traces.append(np.array(trace))
                except (IOError, ValueError):
                    # Handle empty or invalid files gracefully
                    raw_traces.append(np.array([], dtype=bool))


        max_len = max(len(t) for t in raw_traces) if raw_traces else 0
        self.num_timesteps = max_len
        
        self.spot_availability = np.zeros((self.num_regions, self.num_timesteps), dtype=bool)
        for i, trace in enumerate(raw_traces):
            self.spot_availability[i, :len(trace)] = trace

        # Precompute future consecutive spot availability streaks
        self.future_streaks = np.zeros_like(self.spot_availability, dtype=int)
        if self.num_timesteps > 0:
            for r in range(self.num_regions):
                if self.spot_availability[r, -1]:
                    self.future_streaks[r, -1] = 1
                for t in range(self.num_timesteps - 2, -1, -1):
                    if self.spot_availability[r, t]:
                        self.future_streaks[r, t] = 1 + self.future_streaks[r, t + 1]

        # Precompute the index of the next available spot time slot
        self.next_spot_idx = np.full_like(self.spot_availability, self.num_timesteps, dtype=int)
        if self.num_timesteps > 0:
            for r in range(self.num_regions):
                next_spot = self.num_timesteps
                for t in range(self.num_timesteps - 1, -1, -1):
                    if self.spot_availability[r, t]:
                        next_spot = t
                    self.next_spot_idx[r, t] = next_spot

        self.initialized_step = False
        return self

    def _initialize_on_first_step(self):
        """Initializes attributes that depend on the live environment."""
        self.gap_seconds = self.env.gap_seconds
        
        # --- Tunable Parameters ---
        self.SWITCH_STREAK_FACTOR = 1.0
        self.WAIT_SLACK_BUFFER_FACTOR = 2.0
        self.OD_TO_SPOT_SWITCH_FACTOR = 2.0

        self.initialized_step = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized_step:
            self._initialize_on_first_step()
            
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 1e-9:
            return ClusterType.NONE
            
        elapsed_seconds = self.env.elapsed_seconds
        time_left = self.deadline - elapsed_seconds
        
        if time_left <= work_remaining:
            return ClusterType.ON_DEMAND
            
        current_time_idx = min(int(elapsed_seconds // self.gap_seconds), self.num_timesteps - 1)
        current_region = self.env.get_current_region()
        
        slack = time_left - work_remaining
        
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > self.restart_overhead:
                    if self.num_timesteps > 0:
                        current_streak = self.future_streaks[current_region, current_time_idx]
                        if current_streak * self.gap_seconds > self.restart_overhead * self.OD_TO_SPOT_SWITCH_FACTOR:
                            return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            # Spot is not available. Evaluate alternatives.
            best_alt_region = -1
            max_streak = 0
            if self.num_timesteps > 0:
                for r in range(self.num_regions):
                    if r == current_region:
                        continue
                    streak = self.future_streaks[r, current_time_idx]
                    if streak > max_streak:
                        max_streak = streak
                        best_alt_region = r
            
            can_afford_switch = (slack > self.restart_overhead)
            is_switch_worthwhile = (max_streak * self.gap_seconds > self.restart_overhead * self.SWITCH_STREAK_FACTOR)
            
            if best_alt_region != -1 and can_afford_switch and is_switch_worthwhile:
                self.env.switch_region(best_alt_region)
                return ClusterType.SPOT
            
            if self.num_timesteps > 0:
                next_spot_t_idx = self.next_spot_idx[current_region, current_time_idx]
            else:
                next_spot_t_idx = self.num_timesteps

            if next_spot_t_idx < self.num_timesteps:
                wait_time_steps = next_spot_t_idx - current_time_idx
                wait_time_seconds = wait_time_steps * self.gap_seconds
                safety_buffer = self.restart_overhead * self.WAIT_SLACK_BUFFER_FACTOR
                
                if slack > wait_time_seconds + safety_buffer:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND