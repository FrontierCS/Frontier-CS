import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_safe_seek_spot_v1"

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

        self._initialized = False
        return self

    def _ensure_init(self):
        if self._initialized:
            return
        n = self.env.get_num_regions()
        self._obs_total = [0] * n
        self._obs_avail = [0] * n
        self._up_streak = [0] * n
        self._down_streak = [0] * n
        self._consecutive_none = 0
        self._committed_od = False
        self._initialized = True

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        rem = self.task_duration - done
        if rem < 0.0:
            rem = 0.0
        return rem

    def _best_region(self, current_idx: int) -> int:
        # Use a simple Bayesian-smoothed availability score
        a, b = 2.0, 1.0  # prior leaning toward high availability
        best_idx = current_idx
        best_score = -1.0
        n = len(self._obs_total)
        for j in range(n):
            tot = self._obs_total[j]
            avail = self._obs_avail[j]
            score = (avail + a) / (tot + a + b)
            if score > best_score:
                best_score = score
                best_idx = j
        return best_idx

    def _should_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        if self._committed_od:
            return True
        time_left = self.deadline - self.env.elapsed_seconds
        work_left = self._remaining_work()

        # Time to finish on On-Demand if we commit now (include overhead)
        if last_cluster_type == ClusterType.ON_DEMAND:
            extra_overhead = self.remaining_restart_overhead
        else:
            extra_overhead = self.restart_overhead

        t_finish_od = work_left + (extra_overhead if extra_overhead is not None else 0.0)

        # Safety buffer to account for discretization and uncertainties
        gap = self.env.gap_seconds
        buffer = max(2.0 * gap, self.restart_overhead)

        return time_left <= t_finish_od + buffer

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        # If task is already finished or nearly so, choose NONE to avoid extra cost
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()

        # Update observation for current region
        self._obs_total[current_region] += 1
        if has_spot:
            self._obs_avail[current_region] += 1
            self._up_streak[current_region] += 1
            self._down_streak[current_region] = 0
        else:
            self._down_streak[current_region] += 1
            self._up_streak[current_region] = 0

        # If already committed to On-Demand, keep using it
        if self._committed_od or self._should_commit_on_demand(last_cluster_type):
            self._committed_od = True
            self._consecutive_none = 0
            return ClusterType.ON_DEMAND

        # Prefer Spot if available
        if has_spot:
            self._consecutive_none = 0
            return ClusterType.SPOT

        # Spot unavailable: if already on on-demand, continue (shouldn't happen if we always commit to OD once chosen)
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._consecutive_none = 0
            return ClusterType.ON_DEMAND

        # Attempt to position to the best region while waiting (NONE). This doesn't incur cost.
        best_idx = self._best_region(current_region)

        # Switch to best region if it's significantly better or current region has a down streak
        a, b = 2.0, 1.0
        cur_score = (self._obs_avail[current_region] + a) / (self._obs_total[current_region] + a + b)
        best_score = (self._obs_avail[best_idx] + a) / (self._obs_total[best_idx] + a + b)
        threshold_diff = 0.05

        if (best_idx != current_region and (best_score - cur_score) > threshold_diff) or self._down_streak[current_region] >= 3:
            self.env.switch_region(best_idx)

        self._consecutive_none += 1
        return ClusterType.NONE
