import json
import math
from argparse import Namespace
from collections import defaultdict
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "multi_region_optimizer"

    def __init__(self, args):
        super().__init__(args)
        self.spot_availability = None
        self.region_stats = None
        self.time_step = None
        self.initialized = False

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

        # Load spot availability traces
        self.spot_availability = []
        for trace_file in config["trace_files"]:
            with open(trace_file, 'r') as f:
                # Parse trace file - assuming one integer per line
                availability = [int(line.strip()) > 0 for line in f]
                self.spot_availability.append(availability)

        # Pre-compute region statistics
        self._compute_region_stats()

        return self

    def _compute_region_stats(self):
        """Pre-compute statistics for each region to guide decisions."""
        num_regions = len(self.spot_availability)
        self.region_stats = []
        for region_id in range(num_regions):
            avail = self.spot_availability[region_id]
            total_steps = len(avail)
            spot_steps = sum(avail)
            availability_rate = spot_steps / total_steps if total_steps > 0 else 0

            # Calculate longest consecutive spot availability
            max_consecutive = 0
            current = 0
            for a in avail:
                if a:
                    current += 1
                    max_consecutive = max(max_consecutive, current)
                else:
                    current = 0

            self.region_stats.append({
                'availability_rate': availability_rate,
                'max_consecutive': max_consecutive,
                'total_steps': total_steps
            })

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self.time_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
            self.initialized = True
        else:
            self.time_step += 1

        # Calculate progress metrics
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        elapsed_time = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed_time

        # Calculate time needed with different strategies
        steps_needed_on_demand = math.ceil(remaining_work / self.env.gap_seconds)
        steps_needed_on_spot = math.ceil(remaining_work / self.env.gap_seconds)
        
        # Add overhead considerations
        if last_cluster_type != ClusterType.NONE and last_cluster_type != ClusterType.ON_DEMAND:
            steps_needed_on_demand += 1  # Account for switching overhead
        
        time_needed_on_demand = steps_needed_on_demand * self.env.gap_seconds
        time_needed_on_spot = steps_needed_on_spot * self.env.gap_seconds

        # Emergency mode: if we're running out of time, use on-demand
        safety_margin = 2 * self.env.gap_seconds
        if remaining_time < time_needed_on_demand + safety_margin:
            if last_cluster_type != ClusterType.ON_DEMAND and self.remaining_restart_overhead <= 0:
                # Switch to on-demand to ensure completion
                return ClusterType.ON_DEMAND
            else:
                # Already on on-demand or in overhead
                return ClusterType.ON_DEMAND

        # Check if we're ahead of schedule and can wait for spot
        if remaining_time > time_needed_on_spot * 1.5 and has_spot:
            # We have time to use spot
            current_region = self.env.get_current_region()
            region_data = self.spot_availability[current_region]
            
            # Check if we should stay in current region
            if self._should_stay_in_region(current_region, self.time_step):
                if has_spot:
                    return ClusterType.SPOT
                else:
                    # No spot available, check other regions
                    best_region = self._find_best_region(self.time_step)
                    if best_region != current_region:
                        self.env.switch_region(best_region)
                        return ClusterType.SPOT if self.spot_availability[best_region][self.time_step] else ClusterType.NONE
                    return ClusterType.NONE
            else:
                # Consider switching to better region
                best_region = self._find_best_region(self.time_step)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    new_has_spot = self.spot_availability[best_region][self.time_step]
                    return ClusterType.SPOT if new_has_spot else ClusterType.NONE
        
        # Default: use spot if available, otherwise on-demand if behind schedule
        if has_spot:
            return ClusterType.SPOT
        elif remaining_time < time_needed_on_spot * 1.2:
            # Getting close to deadline, use on-demand
            return ClusterType.ON_DEMAND
        else:
            # Wait for spot
            return ClusterType.NONE

    def _should_stay_in_region(self, region_id: int, time_step: int) -> bool:
        """Determine if we should stay in the current region."""
        if time_step >= len(self.spot_availability[region_id]) - 1:
            return False
        
        # Check next few steps for spot availability
        lookahead = min(5, len(self.spot_availability[region_id]) - time_step - 1)
        future_spot = sum(self.spot_availability[region_id][time_step:time_step + lookahead])
        
        return future_spot > 0

    def _find_best_region(self, time_step: int) -> int:
        """Find the best region to switch to based on future spot availability."""
        num_regions = self.env.get_num_regions()
        best_region = self.env.get_current_region()
        best_score = -1
        
        for region_id in range(num_regions):
            if time_step >= len(self.spot_availability[region_id]):
                continue
                
            # Calculate score based on immediate and near-future availability
            lookahead = min(10, len(self.spot_availability[region_id]) - time_step)
            future_availability = self.spot_availability[region_id][time_step:time_step + lookahead]
            
            immediate = 2 if future_availability[0] else 0
            near_future = sum(future_availability[1:])
            score = immediate + near_future
            
            if score > best_score:
                best_score = score
                best_region = region_id
        
        return best_region