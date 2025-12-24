import json
from argparse import Namespace

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

        # Initialize custom attributes
        self.phase = "explore"
        self.explore_time_per_region = 300.0  # seconds
        self.current_explore_region = None
        self.explore_region_start_time = 0.0
        self.region_stats = None
        self.cool_down = 0
        self.cool_down_period = 5  # steps
        self.on_demand_steps = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization of region stats
        if self.region_stats is None:
            num_regions = self.env.get_num_regions()
            self.region_stats = [{"total": 0, "spot": 0} for _ in range(num_regions)]

        cur_region = self.env.get_current_region()

        # Update statistics for current region
        self.region_stats[cur_region]["total"] += 1
        if has_spot:
            self.region_stats[cur_region]["spot"] += 1

        # Exploration phase
        if self.phase == "explore":
            if self.current_explore_region is None:
                self.current_explore_region = 0
                self.explore_region_start_time = self.env.elapsed_seconds
                self.env.switch_region(0)

            # Check if time to switch exploration region
            if (
                self.env.elapsed_seconds - self.explore_region_start_time
                >= self.explore_time_per_region
            ):
                self.current_explore_region += 1
                if self.current_explore_region >= self.env.get_num_regions():
                    # Choose best region based on observed spot probability
                    best_region = 0
                    best_prob = -1.0
                    for i, stats in enumerate(self.region_stats):
                        if stats["total"] > 0:
                            prob = stats["spot"] / stats["total"]
                        else:
                            prob = 0.0
                        if prob > best_prob:
                            best_prob = prob
                            best_region = i
                    self.env.switch_region(best_region)
                    self.phase = "exploit"
                else:
                    self.env.switch_region(self.current_explore_region)
                    self.explore_region_start_time = self.env.elapsed_seconds
            return ClusterType.ON_DEMAND

        # Exploitation phase
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds

        # Critical condition: must use on-demand to meet deadline
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed = remaining_work
        else:
            time_needed = remaining_work + self.restart_overhead
        if self.env.elapsed_seconds + time_needed > self.deadline:
            self.on_demand_steps += 1
            return ClusterType.ON_DEMAND

        # Handle cool-down after preemption
        if self.cool_down > 0:
            self.cool_down -= 1
            self.on_demand_steps += 1
            return ClusterType.ON_DEMAND

        # Spot available and not in cool-down
        if has_spot:
            if last_cluster_type != ClusterType.SPOT:
                # Switch to spot only if we've been on-demand for a while
                if self.on_demand_steps >= self.cool_down_period:
                    self.on_demand_steps = 0
                    return ClusterType.SPOT
                else:
                    self.on_demand_steps += 1
                    return ClusterType.ON_DEMAND
            else:
                self.on_demand_steps = 0
                return ClusterType.SPOT
        else:
            # Spot not available
            if last_cluster_type == ClusterType.SPOT:
                self.cool_down = self.cool_down_period
                self.on_demand_steps = 0
                return ClusterType.ON_DEMAND

            # Decide between on-demand and waiting
            if remaining_time / max(remaining_work, 1e-9) > 2.0:
                # Plenty of slack, wait for spot
                self.on_demand_steps = 0
                return ClusterType.NONE
            else:
                self.on_demand_steps += 1
                return ClusterType.ON_DEMAND
