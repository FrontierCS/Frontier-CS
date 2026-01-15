import json
from argparse import Namespace
import sys

# It is recommended to install pandas for efficient CSV parsing.
# If pandas is not available, a fallback to the standard csv module is provided.
try:
    import pandas as pd
except ImportError:
    pd = None

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant-be-late_v2"

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

        self.trace_files = config["trace_files"]
        self.traces_loaded = False
        self.traces = []
        self.future_spot_counts = []

        return self

    def _lazy_load_traces(self):
        if self.traces_loaded:
            return

        if pd is None:
            sys.stderr.write("Warning: pandas is not installed. Using standard csv module, which may be slower.\n")
            self._load_with_csv()
        else:
            try:
                self._load_with_pandas()
            except Exception as e:
                sys.stderr.write(f"Warning: pandas failed ({e}). Falling back to standard csv module.\n")
                self._load_with_csv()
        
        self._precompute_future_spots()
        self.traces_loaded = True

    def _load_with_pandas(self):
        num_steps = int(self.deadline / self.env.gap_seconds) + 10
        for trace_file in self.trace_files:
            df = pd.read_csv(trace_file)
            if len(df.columns) == 2:
                df.columns = ['timestamp', 'spot_available']
            
            df = df.sort_values(by='timestamp').reset_index(drop=True)

            trace_data = [0] * num_steps
            last_ts = 0.0
            last_avail = 0
            
            initial_state_rows = df[df['timestamp'] <= 0]
            if not initial_state_rows.empty:
                last_avail = int(initial_state_rows.iloc[-1]['spot_available'])

            for _, row in df[df['timestamp'] > 0].iterrows():
                ts = row['timestamp']
                avail = int(row['spot_available'])
                
                start_idx = int(last_ts / self.env.gap_seconds)
                end_idx = int(ts / self.env.gap_seconds)
                
                for i in range(start_idx, min(end_idx, num_steps)):
                    trace_data[i] = last_avail
                
                last_ts = ts
                last_avail = avail

            start_idx = int(last_ts / self.env.gap_seconds)
            for i in range(start_idx, num_steps):
                trace_data[i] = last_avail
            
            self.traces.append(trace_data)

    def _load_with_csv(self):
        import csv
        num_steps = int(self.deadline / self.env.gap_seconds) + 10
        for trace_file in self.trace_files:
            with open(trace_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                ts_idx = header.index('timestamp')
                avail_idx = header.index('spot_available')
                
                rows = sorted([(float(row[ts_idx]), int(row[avail_idx])) for row in reader])

            trace_data = [0] * num_steps
            last_ts = 0.0
            last_avail = 0
            
            initial_state_rows = [r for r in rows if r[0] <= 0]
            if initial_state_rows:
                last_avail = initial_state_rows[-1][1]

            for ts, avail in [r for r in rows if r[0] > 0]:
                start_idx = int(last_ts / self.env.gap_seconds)
                end_idx = int(ts / self.env.gap_seconds)
                
                for i in range(start_idx, min(end_idx, num_steps)):
                    trace_data[i] = last_avail
                
                last_ts = ts
                last_avail = avail

            start_idx = int(last_ts / self.env.gap_seconds)
            for i in range(start_idx, num_steps):
                trace_data[i] = last_avail
            
            self.traces.append(trace_data)

    def _precompute_future_spots(self):
        if not self.traces:
            return
        num_steps = len(self.traces[0])
        num_regions = len(self.traces)
        self.future_spot_counts = []
        for r in range(num_regions):
            counts = [0] * num_steps
            if num_steps > 0:
                if self.traces[r][num_steps - 1] == 1:
                    counts[num_steps - 1] = 1
            for i in range(num_steps - 2, -1, -1):
                if self.traces[r][i] == 1:
                    counts[i] = 1 + counts[i + 1]
            self.future_spot_counts.append(counts)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.traces_loaded:
            self._lazy_load_traces()

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        current_timestep = int(elapsed_time / self.env.gap_seconds)

        if current_timestep >= len(self.traces[0]):
            return ClusterType.ON_DEMAND

        time_left = self.deadline - elapsed_time

        time_needed_if_od = work_remaining + self.restart_overhead
        if time_needed_if_od >= time_left:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        slack = time_left - work_remaining
        current_region = self.env.get_current_region()

        best_alt_region = -1
        max_future_spot = 0
        num_regions = self.env.get_num_regions()

        for r in range(num_regions):
            if r == current_region:
                continue
            
            if self.traces[r][current_timestep] == 1:
                future_spot = self.future_spot_counts[r][current_timestep]
                if future_spot > max_future_spot:
                    max_future_spot = future_spot
                    best_alt_region = r

        if best_alt_region != -1 and slack > self.restart_overhead:
            self.env.switch_region(best_alt_region)
            return ClusterType.SPOT

        if slack > self.restart_overhead + self.env.gap_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND