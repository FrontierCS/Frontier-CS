import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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

        # Custom state initialization
        self._mr_initialized = False
        self._mr_done_work = 0.0
        self._mr_last_task_len = len(getattr(self, "task_done_time", []))
        self._mr_num_regions = 1
        self._mr_spot_success = []
        self._mr_region_steps = []
        self._mr_global_steps = 0
        self.committed_to_od = False

        return self

    def _initialize_regions(self):
        if self._mr_initialized:
            return
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        if num_regions <= 0:
            num_regions = 1
        self._mr_num_regions = num_regions
        self._mr_spot_success = [0] * num_regions
        self._mr_region_steps = [0] * num_regions
        self._mr_global_steps = 0
        self._mr_initialized = True

    def _update_done_work(self):
        current_list = getattr(self, "task_done_time", [])
        current_len = len(current_list)
        if current_len > self._mr_last_task_len:
            # Incremental sum of new segments
            new_sum = 0.0
            for i in range(self._mr_last_task_len, current_len):
                new_sum += current_list[i]
            self._mr_done_work += new_sum
            self._mr_last_task_len = current_len
        elif current_len < self._mr_last_task_len:
            # Environment reset or unexpected change; recompute safely
            total = 0.0
            for v in current_list:
                total += v
            self._mr_done_work = total
            self._mr_last_task_len = current_len

    def _select_best_region_for_next_step(self, current_region: int):
        # UCB1 over regions based on spot availability frequency
        num_regions = self._mr_num_regions
        total_steps = self._mr_global_steps
        if total_steps <= 0:
            best_region = current_region
        else:
            best_region = current_region
            best_score = -1.0
            log_total = math.log(total_steps)
            for i in range(num_regions):
                n = self._mr_region_steps[i]
                if n == 0:
                    score = float("inf")
                else:
                    p = self._mr_spot_success[i] / n
                    bonus = math.sqrt(max(0.0, 2.0 * log_total / n))
                    score = p + bonus
                if score > best_score:
                    best_score = score
                    best_region = i
        if best_region != current_region:
            try:
                self.env.switch_region(best_region)
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_regions()
        self._update_done_work()

        # Determine current region index safely
        try:
            current_region = self.env.get_current_region()
        except Exception:
            current_region = 0
        if not isinstance(current_region, int) or not (0 <= current_region < self._mr_num_regions):
            current_region = 0

        # Update region spot statistics
        self._mr_global_steps += 1
        self._mr_region_steps[current_region] += 1
        if has_spot:
            self._mr_spot_success[current_region] += 1

        # Choose region for next step via UCB
        self._select_best_region_for_next_step(current_region)

        # Compute remaining work and time
        remaining_work = max(0.0, self.task_duration - self._mr_done_work)
        time_left = self.deadline - getattr(self.env, "elapsed_seconds", 0.0)
        if time_left < 0.0:
            time_left = 0.0

        # Decide when to permanently switch to on-demand
        if not self.committed_to_od and remaining_work > 0.0:
            gap = getattr(self.env, "gap_seconds", 0.0)
            # Need remaining_work + restart_overhead (+ margin) time to finish on on-demand
            margin = remaining_work + self.restart_overhead + 2.0 * gap
            if time_left <= margin:
                self.committed_to_od = True

        # If work is done, no need to run any cluster
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # After commitment, always use on-demand to ensure deadline
        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        # Before commitment: use spot when available, otherwise wait
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE