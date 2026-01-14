import json
from argparse import Namespace
from typing import List, Tuple
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cautious_hybrid_optimizer"

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
        
        # Load traces
        self.trace_files = config["trace_files"]
        self.spot_availability = self._load_traces()
        self.num_regions = len(self.trace_files)
        
        # Parameters from problem description
        self.spot_price = 0.9701 / 3600  # $ per second
        self.ondemand_price = 3.06 / 3600  # $ per second
        
        # State tracking
        self.current_region = 0
        self.last_decision = None
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 3  # Switch to on-demand after this many consecutive spot unavailability
        
        # Dynamic thresholds based on remaining time
        self.safe_threshold = 0.7  # Use spot when time buffer > 70% of remaining work
        self.critical_threshold = 0.3  # Switch to on-demand when time buffer < 30%
        
        return self
    
    def _load_traces(self) -> List[List[bool]]:
        """Load spot availability traces from files."""
        availability = []
        for trace_file in self.trace_files:
            with open(trace_file, 'r') as f:
                # Assuming trace files contain one value per line (0/1 or True/False)
                lines = f.readlines()
                region_avail = [bool(int(line.strip())) for line in lines if line.strip()]
                availability.append(region_avail)
        return availability
    
    def _get_current_time_index(self) -> int:
        """Convert elapsed seconds to time step index."""
        return int(self.env.elapsed_seconds // self.env.gap_seconds)
    
    def _calculate_time_pressure(self) -> float:
        """Calculate how pressed for time we are (0 = lots of time, 1 = critical)."""
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return 0.0
        
        # Time needed if we could work continuously
        min_time_needed = work_remaining
        if remaining_time <= 0:
            return 1.0
        
        time_buffer = remaining_time - min_time_needed
        max_buffer = self.deadline - self.task_duration  # Maximum possible buffer
        
        if max_buffer <= 0:
            return 1.0
        
        pressure = 1.0 - (time_buffer / max_buffer)
        return max(0.0, min(1.0, pressure))
    
    def _find_best_region(self) -> int:
        """Find the region with best future spot availability."""
        current_idx = self._get_current_time_index()
        best_region = self.current_region
        best_score = 0
        
        # Look ahead window (conservative)
        lookahead = min(10, len(self.spot_availability[0]) - current_idx)
        
        for region in range(self.num_regions):
            if current_idx >= len(self.spot_availability[region]):
                continue
                
            # Score based on immediate and near-future availability
            window = self.spot_availability[region][current_idx:current_idx + lookahead]
            if not window:
                continue
                
            # Prefer regions with consistent spot availability
            immediate_score = 2.0 if window[0] else 0.0
            future_score = sum(1 for avail in window[1:] if avail) / max(1, len(window) - 1)
            total_score = immediate_score + future_score
            
            if total_score > best_score:
                best_score = total_score
                best_region = region
        
        return best_region
    
    def _should_switch_region(self) -> bool:
        """Determine if we should switch to a different region."""
        current_idx = self._get_current_time_index()
        
        # Don't switch if we're in a restart overhead period
        if self.remaining_restart_overhead > 0:
            return False
        
        # Check if current region has spot available now
        if (current_idx < len(self.spot_availability[self.current_region]) and 
            self.spot_availability[self.current_region][current_idx]):
            return False
        
        # Find better region
        best_region = self._find_best_region()
        if best_region != self.current_region:
            # Only switch if the target region has spot available now
            if (current_idx < len(self.spot_availability[best_region]) and 
                self.spot_availability[best_region][current_idx]):
                return True
        
        return False
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update current region from environment
        self.current_region = self.env.get_current_region()
        
        # Calculate work progress and time pressure
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_pressure = self._calculate_time_pressure()
        
        # If work is complete, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # If we're in critical time pressure, use on-demand
        if time_pressure > self.critical_threshold:
            self.consecutive_spot_failures = 0
            return ClusterType.ON_DEMAND
        
        # Check if we should switch regions
        if self._should_switch_region():
            best_region = self._find_best_region()
            if best_region != self.current_region:
                self.env.switch_region(best_region)
                self.current_region = best_region
                # After switching, we need to restart, so use appropriate type
                current_idx = self._get_current_time_index()
                if (current_idx < len(self.spot_availability[self.current_region]) and 
                    self.spot_availability[self.current_region][current_idx]):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        # Check current region's spot availability
        current_idx = self._get_current_time_index()
        current_has_spot = False
        if current_idx < len(self.spot_availability[self.current_region]):
            current_has_spot = self.spot_availability[self.current_region][current_idx]
        
        # If spot is available and we have time buffer, use spot
        if current_has_spot and time_pressure < self.safe_threshold:
            self.consecutive_spot_failures = 0
            return ClusterType.SPOT
        
        # If spot is not available but we still have some buffer
        if not current_has_spot and time_pressure < self.safe_threshold:
            self.consecutive_spot_failures += 1
            if self.consecutive_spot_failures >= self.max_spot_failures:
                # Too many consecutive failures, use on-demand temporarily
                return ClusterType.ON_DEMAND
            else:
                # Wait for spot to become available
                return ClusterType.NONE
        
        # Default to on-demand for moderate time pressure or when unsure
        self.consecutive_spot_failures = 0
        return ClusterType.ON_DEMAND