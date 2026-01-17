import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_v1"

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
        # Internal states (lazy-init some in _step when env is available)
        self._init_done = False
        self._od_committed = False
        self._done_sum = 0.0
        self._done_len = 0
        self._last_region = None
        self._region_success = None
        self._region_visits = None
        self._prior_success = 1.0
        self._prior_total = 2.0
        return self

    def _lazy_init(self):
        if self._init_done:
            return
        num_regions = 1
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 1
        self._region_success = [0.0] * num_regions
        self._region_visits = [0.0] * num_regions
        self._init_done = True

    def _update_progress_sum(self):
        cur_len = len(self.task_done_time)
        if cur_len > self._done_len:
            # Incrementally update sum to avoid O(n^2)
            add = 0.0
            for i in range(self._done_len, cur_len):
                add += self.task_done_time[i]
            self._done_sum += add
            self._done_len = cur_len

    def _best_region(self, current_idx: int) -> int:
        # Choose region with highest smoothed availability estimate
        # score = (succ + prior_success) / (visits + prior_total)
        best_idx = current_idx
        best_score = -1.0
        n = len(self._region_success)
        for i in range(n):
            score = (self._region_success[i] + self._prior_success) / (
                self._region_visits[i] + self._prior_total
            )
            if score > best_score or (score == best_score and i == current_idx):
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update observation statistics for current region
        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0
        if current_region < 0 or current_region >= len(self._region_success):
            current_region = 0

        # Record spot availability observation
        self._region_visits[current_region] += 1.0
        if has_spot:
            self._region_success[current_region] += 1.0

        # Update progress and remaining work/time
        self._update_progress_sum()
        remaining_work = max(0.0, self.task_duration - self._done_sum)
        time_left = self.deadline - self.env.elapsed_seconds
        gap = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)

        # If already committed to OD, stay on OD to avoid risk and extra overheads
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Slack relative to "start OD now and finish in time"
        # slack = T_left - (W_rem + restart_overhead)
        slack = time_left - (remaining_work + ro)

        # If no time left or close to deadline, commit to OD
        # Commit when we cannot safely afford to lose another time step (gap).
        if slack < gap:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Otherwise, we are in SPOT-favor mode
        if has_spot:
            # If spot available, use it
            return ClusterType.SPOT

        # Spot not available in current region, and we have slack; wait and probe a better region
        # Switch to the region with highest observed availability and wait (NONE) this step
        best_region = self._best_region(current_region)
        if best_region != current_region:
            try:
                self.env.switch_region(best_region)
            except Exception:
                pass
        return ClusterType.NONE