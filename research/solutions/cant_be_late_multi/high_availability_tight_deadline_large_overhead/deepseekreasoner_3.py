import json
from argparse import Namespace
from collections import defaultdict
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    NAME = "dynamic_risk_scheduler"

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

        self.traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                self.traces.append([int(line.strip()) for line in f])
        
        self.num_regions = len(self.traces)
        self.trace_length = len(self.traces[0]) if self.traces else 0
        self.spot_price = 0.9701
        self.on_demand_price = 3.06
        self.hour_steps = int(3600 // self.env.gap_seconds)
        
        self.initialize_spot_patterns()
        
        return self

    def initialize_spot_patterns(self):
        self.spot_windows = []
        for region_idx in range(self.num_regions):
            windows = []
            start = -1
            for i in range(self.trace_length):
                if self.traces[region_idx][i]:
                    if start == -1:
                        start = i
                else:
                    if start != -1:
                        windows.append((start, i-1))
                        start = -1
            if start != -1:
                windows.append((start, self.trace_length-1))
            self.spot_windows.append(windows)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        deadline_step = int(self.deadline / self.env.gap_seconds)
        remaining_work = self.task_duration - sum(self.task_done_time)
        current_region = self.env.get_current_region()
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        remaining_steps = deadline_step - current_step
        required_steps = math.ceil(remaining_work / self.env.gap_seconds)
        
        if required_steps > remaining_steps:
            return ClusterType.ON_DEMAND
            
        current_hour = current_step // self.hour_steps
        
        best_region, best_availability = self.find_best_region(current_hour, required_steps)
        
        if best_region != current_region:
            self.env.switch_region(best_region)
            current_region = best_region
            has_spot = self.traces[best_region][current_hour]
        
        if self.should_use_ondemand(current_hour, required_steps, remaining_steps, remaining_work):
            return ClusterType.ON_DEMAND
            
        if has_spot:
            risk = self.calculate_risk(current_region, current_hour, required_steps)
            if risk < 0.3:
                return ClusterType.SPOT
        
        return ClusterType.ON_DEMAND

    def find_best_region(self, current_hour: int, required_steps: int) -> tuple:
        best_region = self.env.get_current_region()
        best_availability = 0
        
        for region in range(self.num_regions):
            available = 0
            for h in range(current_hour, min(current_hour + required_steps + 1, self.trace_length)):
                if self.traces[region][h]:
                    available += 1
                else:
                    break
            if available > best_availability:
                best_availability = available
                best_region = region
        
        return best_region, best_availability

    def calculate_risk(self, region: int, current_hour: int, required_steps: int) -> float:
        if not self.traces[region][current_hour]:
            return 1.0
            
        future_availability = 0
        lookahead = min(required_steps * 2, 12)
        
        for h in range(current_hour + 1, min(current_hour + lookahead, self.trace_length)):
            if self.traces[region][h]:
                future_availability += 1
            else:
                break
        
        risk = 1.0 - (future_availability / lookahead)
        
        for window_start, window_end in self.spot_windows[region]:
            if window_start <= current_hour <= window_end:
                window_size = window_end - window_start + 1
                if window_size >= required_steps:
                    risk *= 0.5
                break
        
        return risk

    def should_use_ondemand(self, current_hour: int, required_steps: int, 
                          remaining_steps: int, remaining_work: float) -> bool:
        time_ratio = required_steps / remaining_steps
        
        if time_ratio > 0.8:
            return True
            
        if remaining_work <= self.env.gap_seconds * 2:
            return True
            
        overhead_steps = math.ceil(self.restart_overhead / self.env.gap_seconds)
        if required_steps + overhead_steps > remaining_steps * 0.9:
            return True
            
        return False