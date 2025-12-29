import json
from argparse import Namespace
from typing import List, Tuple
import heapq
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
        
        self.time_step = self.env.gap_seconds
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.spot_to_ondemand_ratio = self.ondemand_price / self.spot_price
        
        self.region_history = []
        self.spot_history = []
        self.work_history = []
        
        self.regions_seen = set()
        self.best_regions = []
        
        return self

    def _update_history(self, region_idx: int, has_spot: bool, work_done: float):
        self.region_history.append(region_idx)
        self.spot_history.append(has_spot)
        self.work_history.append(work_done)
        self.regions_seen.add(region_idx)

    def _analyze_regions(self) -> List[Tuple[float, int]]:
        if not self.region_history:
            return []
            
        region_stats = {}
        for i in range(self.env.get_num_regions()):
            region_stats[i] = {"spot_count": 0, "total_steps": 0, "work_done": 0.0}
        
        for idx, region in enumerate(self.region_history):
            stats = region_stats[region]
            stats["total_steps"] += 1
            if self.spot_history[idx]:
                stats["spot_count"] += 1
            stats["work_done"] += self.work_history[idx]
        
        region_scores = []
        for region, stats in region_stats.items():
            if stats["total_steps"] == 0:
                continue
            spot_availability = stats["spot_count"] / stats["total_steps"]
            efficiency = stats["work_done"] / (stats["total_steps"] * self.time_step) if stats["total_steps"] > 0 else 0
            score = spot_availability * efficiency
            region_scores.append((score, region))
        
        region_scores.sort(reverse=True)
        return region_scores

    def _calculate_critical_time(self) -> Tuple[float, float]:
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration[0] - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        time_needed_ondemand = work_remaining
        if self.remaining_restart_overhead > 0:
            time_needed_ondemand += self.remaining_restart_overhead
        
        time_needed_spot = work_remaining
        if self.remaining_restart_overhead > 0:
            time_needed_spot += self.remaining_restart_overhead
        time_needed_spot *= 1.2
        
        return time_needed_ondemand, time_needed_spot, time_remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_region = self.env.get_current_region()
        work_done = self.task_done_time[-1] if self.task_done_time else 0
        self._update_history(current_region, has_spot, work_done)
        
        time_needed_ondemand, time_needed_spot, time_remaining = self._calculate_critical_time()
        
        region_scores = self._analyze_regions()
        best_regions = [r for _, r in region_scores[:3]]
        
        if best_regions and current_region not in best_regions:
            if len(self.regions_seen) > 1 and time_remaining > time_needed_ondemand * 1.5:
                best_region = best_regions[0]
                self.env.switch_region(best_region)
                return ClusterType.NONE
        
        if last_cluster_type == ClusterType.NONE and has_spot:
            return ClusterType.SPOT
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            return ClusterType.ON_DEMAND
        
        if last_cluster_type == ClusterType.ON_DEMAND and has_spot:
            if time_remaining > time_needed_ondemand * 1.2:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if time_remaining < time_needed_ondemand * 1.1:
            return ClusterType.ON_DEMAND
        
        if time_remaining < time_needed_spot:
            return ClusterType.ON_DEMAND
        
        if has_spot:
            if self.remaining_restart_overhead > 0:
                return ClusterType.NONE
            return ClusterType.SPOT
        
        return ClusterType.NONE