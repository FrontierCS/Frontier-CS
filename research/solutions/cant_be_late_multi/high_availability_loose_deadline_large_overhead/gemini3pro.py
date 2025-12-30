import json
import csv
import bisect
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        Also attempts to load availability traces for smart decision making.
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

        # Load traces to guide region switching
        self.traces = []
        trace_paths = config.get("trace_files", [])
        
        for path in trace_paths:
            region_trace = []
            try:
                with open(path, 'r') as f:
                    # Detect header
                    pos = f.tell()
                    first_line = f.readline()
                    f.seek(pos)
                    
                    has_header = False
                    if first_line:
                        parts = first_line.strip().split(',')
                        try:
                            float(parts[0])
                        except ValueError:
                            has_header = True
                    
                    reader = csv.reader(f)
                    if has_header:
                        next(reader, None)
                        
                    for row in reader:
                        if len(row) >= 2:
                            try:
                                t = float(row[0])
                                # Parse availability boolean from various formats
                                val_str = row[1].lower()
                                is_avail = val_str in ('true', '1', 'up', 'available')
                                region_trace.append((t, is_avail))
                            except ValueError:
                                continue
            except Exception:
                # Fallback to empty trace if load fails
                pass
            
            # Ensure chronological order for binary search
            region_trace.sort(key=lambda x: x[0])
            self.traces.append(region_trace)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Prioritizes:
        1. Meeting Deadline (Switch to OD if tight).
        2. Using Spot in current region (Cheapest/Fastest).
        3. Switching to a region with known Spot availability (via traces).
        4. Rotating regions blindly (Fallback).
        """
        # --- 1. Gather Metrics ---
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_needed = self.task_duration - work_done
        
        # If finished (should be handled by env, but for safety)
        if work_needed <= 1e-6:
            return ClusterType.NONE

        time_left = self.deadline - current_time
        gap_sec = self.env.gap_seconds
        overhead_sec = self.restart_overhead

        # --- 2. Deadline Safeguard (Panic Mode) ---
        # Calculate time required if we switch to On-Demand NOW.
        # If currently on OD, no extra overhead. If Spot/None, we pay overhead to start OD.
        od_setup_cost = overhead_sec if last_cluster_type != ClusterType.ON_DEMAND else 0.0
        
        # Safety buffer: 2 steps to account for decision granularity
        safety_buffer = 2.0 * gap_sec
        
        # If remaining time is critically low, force On-Demand
        if time_left < (work_needed + od_setup_cost + safety_buffer):
            return ClusterType.ON_DEMAND

        # --- 3. Greedy Spot Strategy ---
        # If Spot is available in the current region, use it immediately.
        # This minimizes restart overheads caused by switching regions.
        if has_spot:
            return ClusterType.SPOT

        # --- 4. Spot Hunting (Multi-Region) ---
        # Current region has no Spot. We must find one.
        current_region_idx = self.env.get_current_region()
        best_region = -1
        
        # Use traces to find a region that is UP at current_time
        if self.traces:
            for ridx, trace in enumerate(self.traces):
                if ridx == current_region_idx:
                    continue # Already know it's down
                if not trace:
                    continue
                
                # Binary search to find status at current_time
                # Find rightmost entry <= current_time
                idx = bisect.bisect_right(trace, (current_time, True)) - 1
                if idx >= 0:
                    # Check status
                    if trace[idx][1]: # Available
                        best_region = ridx
                        break
        
        if best_region != -1:
            self.env.switch_region(best_region)
            # We trust the trace and assume Spot is available in new region
            return ClusterType.SPOT
            
        # --- 5. Fallback Strategy ---
        # If no trace info or all regions appear down:
        # Switch to next region and WAIT (NONE).
        # We return NONE to avoid "Error if False" penalty if the new region is also down.
        # In the next step, we will verify availability via 'has_spot'.
        next_region = (current_region_idx + 1) % self.env.get_num_regions()
        self.env.switch_region(next_region)
        return ClusterType.NONE