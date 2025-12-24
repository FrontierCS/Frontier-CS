import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ucb_v1"

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

        self._init_done = False
        self._work_done_sum = 0.0
        self._task_done_idx = 0

        self._n_regions = 1
        self._region_seen = None
        self._region_spot = None
        self._total_seen = 0

        self._ucb_c = 0.8
        self._eps = 1e-9
        self._last_idle_switch_t = -1.0

        return self

    def _lazy_init(self) -> None:
        if self._init_done:
            return
        try:
            self._n_regions = int(self.env.get_num_regions())
        except Exception:
            self._n_regions = 1
        if self._n_regions <= 0:
            self._n_regions = 1
        self._region_seen = [0] * self._n_regions
        self._region_spot = [0] * self._n_regions
        self._total_seen = 0
        self._init_done = True

    def _update_work_done(self) -> None:
        td = self.task_done_time
        idx = self._task_done_idx
        n = len(td)
        if idx >= n:
            return
        s = self._work_done_sum
        for i in range(idx, n):
            s += float(td[i])
        self._work_done_sum = s
        self._task_done_idx = n

    def _choose_next_region_ucb(self, current_region: int) -> int:
        n = self._n_regions
        if n <= 1:
            return current_region

        total = self._total_seen
        logt = math.log(total + 1.0) if total > 0 else 0.0

        best_r = current_region
        best_score = -1e30

        for r in range(n):
            if r == current_region:
                continue
            seen = self._region_seen[r]
            spot = self._region_spot[r]
            mean = (spot + 1.0) / (seen + 2.0)
            bonus = self._ucb_c * math.sqrt(logt / (seen + 1.0)) if logt > 0.0 else 0.0
            score = mean + bonus
            if score > best_score + 1e-15:
                best_score = score
                best_r = r
        return best_r

    def _progress_if_run(self, chosen: ClusterType, last_cluster_type: ClusterType, dt: float) -> float:
        if chosen == ClusterType.NONE:
            return 0.0
        if chosen == last_cluster_type:
            overhead_begin = float(self.remaining_restart_overhead)
        else:
            overhead_begin = float(self.restart_overhead)
        overhead_processed = overhead_begin if overhead_begin < dt else dt
        prog = dt - overhead_processed
        return prog if prog > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update region stats for the region whose availability we observed this step.
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if 0 <= cur_region < self._n_regions:
            self._region_seen[cur_region] += 1
            if has_spot:
                self._region_spot[cur_region] += 1
            self._total_seen += 1

        # Update cached work done in O(delta) time.
        self._update_work_done()

        remaining_work = float(self.task_duration) - float(self._work_done_sum)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        dt = float(self.env.gap_seconds)
        if dt <= 0.0:
            return ClusterType.NONE

        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        if remaining_time <= 0.0:
            return ClusterType.NONE

        time_after = remaining_time - dt

        # Conservative feasibility checks:
        # If we do nothing now, can we still finish by running ON_DEMAND from next step onward?
        none_safe = time_after >= (remaining_work + float(self.restart_overhead)) - self._eps

        # If we run SPOT now, can we still finish by running ON_DEMAND from next step onward?
        spot_safe = False
        prog_spot = 0.0
        if has_spot:
            prog_spot = self._progress_if_run(ClusterType.SPOT, last_cluster_type, dt)
            rem_after_spot = remaining_work - prog_spot
            if rem_after_spot < 0.0:
                rem_after_spot = 0.0
            spot_safe = time_after >= (rem_after_spot + float(self.restart_overhead)) - self._eps

        # If we run ON_DEMAND now (and keep doing so), is it feasible at all?
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_now = float(self.remaining_restart_overhead)
        else:
            overhead_now = float(self.restart_overhead)
        feasible_if_od_now = remaining_time >= (remaining_work + overhead_now) - self._eps

        # Prefer SPOT when safe, except avoid switching from ON_DEMAND too close to deadline.
        if has_spot and spot_safe:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Avoid paying a restart overhead on a switch when time is tight or work is tiny.
                slack = remaining_time - remaining_work
                min_work_to_switch = 3.0 * float(self.restart_overhead)
                if slack <= 2.0 * float(self.restart_overhead) + self._eps or remaining_work <= min_work_to_switch + self._eps:
                    # If we must compute now, keep ON_DEMAND; otherwise, allow NONE below.
                    if not none_safe or not feasible_if_od_now:
                        return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT
            else:
                return ClusterType.SPOT

        # If SPOT is unavailable or unsafe, pause if it's safe; while paused, switch regions to hunt for spot.
        if none_safe:
            if (not has_spot) and self._n_regions > 1:
                nxt = self._choose_next_region_ucb(cur_region)
                if nxt != cur_region:
                    try:
                        self.env.switch_region(int(nxt))
                    except Exception:
                        pass
            return ClusterType.NONE

        # Otherwise, run ON_DEMAND to protect deadline.
        return ClusterType.ON_DEMAND
