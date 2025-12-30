import json
from argparse import Namespace
from typing import List, Tuple, Dict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"
    
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
        
        # Load and preprocess traces
        self.traces = self._load_traces(config["trace_files"])
        self.num_regions = len(self.traces)
        self.timesteps = len(self.traces[0])
        
        # Precompute spot availability patterns
        self._precompute_availability()
        
        # Initialize state
        self.current_region = 0
        self.last_action = ClusterType.NONE
        self.consecutive_spot = 0
        self.consecutive_ondemand = 0
        
        return self
    
    def _load_traces(self, trace_files: List[str]) -> List[List[bool]]:
        traces = []
        for filepath in trace_files:
            with open(filepath, 'r') as f:
                # Parse trace file - assuming one availability value per line
                trace = [line.strip() == "1" for line in f if line.strip()]
                traces.append(trace)
        return traces
    
    def _precompute_availability(self):
        # Precompute spot availability metrics for each region
        self.spot_density = []
        self.spot_streaks = []
        
        for region_idx in range(self.num_regions):
            trace = self.traces[region_idx]
            # Compute spot density (fraction of timesteps with spot available)
            density = sum(trace) / len(trace)
            self.spot_density.append(density)
            
            # Compute streak information
            streaks = []
            current_streak = 0
            for available in trace:
                if available:
                    current_streak += 1
                else:
                    if current_streak > 0:
                        streaks.append(current_streak)
                    current_streak = 0
            if current_streak > 0:
                streaks.append(current_streak)
            
            self.spot_streaks.append(streaks)
    
    def _get_region_score(self, region_idx: int, current_time_idx: int) -> float:
        trace = self.traces[region_idx]
        remaining_timesteps = min(self.timesteps - current_time_idx, 100)  # Look ahead 100 timesteps
        
        if remaining_timesteps <= 0:
            return -float('inf')
        
        # Calculate immediate and near-future spot availability
        immediate_available = 1 if trace[current_time_idx] else 0
        lookahead = min(10, remaining_timesteps)
        near_future = sum(trace[current_time_idx:current_time_idx + lookahead]) / lookahead
        
        # Consider overall spot density
        density = self.spot_density[region_idx]
        
        # Weighted score favoring regions with good immediate and near-future availability
        score = (0.4 * immediate_available + 0.4 * near_future + 0.2 * density)
        return score
    
    def _should_switch_region(self, current_region: int, current_time_idx: int) -> Tuple[bool, int]:
        current_score = self._get_region_score(current_region, current_time_idx)
        best_region = current_region
        best_score = current_score
        
        for region_idx in range(self.num_regions):
            if region_idx == current_region:
                continue
            
            score = self._get_region_score(region_idx, current_time_idx)
            if score > best_score + 0.1:  # Threshold to avoid unnecessary switches
                best_score = score
                best_region = region_idx
        
        return best_region != current_region, best_region
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_time_idx = int(current_time / gap)
        
        # Update internal state
        self.current_region = self.env.get_current_region()
        
        # Calculate progress metrics
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - current_time
        
        # Calculate conservative time estimates
        conservative_time_needed = remaining_work
        if last_cluster_type == ClusterType.NONE:
            conservative_time_needed += self.restart_overhead
        
        # Check if we're in a time-critical situation
        time_critical = time_left < conservative_time_needed * 1.5
        
        # Update consecutive counters
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.consecutive_spot += 1
            self.consecutive_ondemand = 0
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_ondemand += 1
            self.consecutive_spot = 0
        else:
            self.consecutive_spot = 0
            self.consecutive_ondemand = 0
        
        # If time is critical, use on-demand to guarantee completion
        if time_critical:
            should_switch, best_region = self._should_switch_region(self.current_region, current_time_idx)
            if should_switch:
                self.env.switch_region(best_region)
                self.current_region = best_region
            return ClusterType.ON_DEMAND
        
        # Check if we should switch regions for better spot availability
        should_switch, best_region = self._should_switch_region(self.current_region, current_time_idx)
        
        # If switching would help and we're not in the middle of work, consider switching
        if should_switch and self.remaining_restart_overhead == 0:
            # Only switch if the benefit outweighs the cost
            trace_current = self.traces[self.current_region]
            trace_best = self.traces[best_region]
            
            # Check immediate availability in both regions
            current_avail = trace_current[current_time_idx] if current_time_idx < len(trace_current) else False
            best_avail = trace_best[current_time_idx] if current_time_idx < len(trace_best) else False
            
            # Switch if target region has spot and current doesn't, or if target is significantly better
            if (not current_avail and best_avail) or (self.spot_density[best_region] > self.spot_density[self.current_region] + 0.15):
                self.env.switch_region(best_region)
                self.current_region = best_region
                has_spot = best_avail
        
        # Decision logic based on spot availability and state
        if has_spot:
            # Use spot if available, but be cautious after interruptions
            if self.remaining_restart_overhead > 0:
                # If we're in restart overhead, continue with same type if possible
                if last_cluster_type == ClusterType.SPOT:
                    return ClusterType.SPOT
                else:
                    # Consider on-demand if restart overhead is large and we need to catch up
                    if remaining_work > time_left * 0.8:
                        return ClusterType.ON_DEMAND
                    return ClusterType.SPOT
            else:
                return ClusterType.SPOT
        else:
            # No spot available
            if self.consecutive_ondemand < 3 and remaining_work > 0:
                # Use on-demand sparingly, but ensure progress
                return ClusterType.ON_DEMAND
            else:
                # Pause to wait for spot or switch regions
                return ClusterType.NONE