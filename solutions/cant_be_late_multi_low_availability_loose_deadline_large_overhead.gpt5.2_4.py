import json
import math
from argparse import Namespace
from typing import Optional, List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        self._reset_internal_state()
        return self

    def _reset_internal_state(self) -> None:
        self._inited = False
        self._n_regions = 0

        self._seen = None
        self._avail = None
        self._last_spot_ts = None

        self._prev_task_done_len = 0
        self._work_done = 0.0

        self._last_switch_ts = -1e30

        self._tau_recency = 6.0 * 3600.0
        self._recency_weight = 0.20
        self._ucb_c = 0.35

        self._switch_min_interval = None
        self._switch_improve_delta = 0.03

    @staticmethod
    def _as_scalar_seconds(x) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0])
        return float(x)

    def _ensure_init(self) -> None:
        if self._inited:
            return
        self._n_regions = int(self.env.get_num_regions())
        self._seen = [0] * self._n_regions
        self._avail = [0] * self._n_regions
        self._last_spot_ts = [-1e30] * self._n_regions
        gap = float(self.env.gap_seconds)
        self._switch_min_interval = max(gap, 900.0)
        self._inited = True

    def _update_work_done(self) -> None:
        tdt = self.task_done_time
        if not tdt:
            return
        l = len(tdt)
        if l <= self._prev_task_done_len:
            return
        if l == self._prev_task_done_len + 1:
            self._work_done += float(tdt[-1])
        else:
            self._work_done += float(sum(tdt[self._prev_task_done_len :]))
        self._prev_task_done_len = l

    def _region_score(self, idx: int, elapsed: float, total_seen: int) -> float:
        seen = self._seen[idx]
        avail = self._avail[idx]
        p = (avail + 1.0) / (seen + 2.0)
        explore = self._ucb_c * math.sqrt(max(0.0, math.log(total_seen + 1.0)) / (seen + 1.0))
        last_ts = self._last_spot_ts[idx]
        rec = 0.0
        if last_ts > -1e20:
            rec = math.exp(-max(0.0, elapsed - last_ts) / self._tau_recency)
        return p + explore + self._recency_weight * rec

    def _choose_region_to_wait(self, elapsed: float, current_region: int) -> Tuple[int, float, float]:
        total_seen = sum(self._seen) + 1
        best_r = current_region
        best_s = -1e30
        cur_s = -1e30
        for i in range(self._n_regions):
            s = self._region_score(i, elapsed, total_seen)
            if i == current_region:
                cur_s = s
            if s > best_s:
                best_s = s
                best_r = i
        return best_r, best_s, cur_s

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_work_done()

        task_duration = self._as_scalar_seconds(self.task_duration)
        deadline = self._as_scalar_seconds(self.deadline)
        restart_overhead = self._as_scalar_seconds(self.restart_overhead)
        gap = float(self.env.gap_seconds)

        elapsed = float(self.env.elapsed_seconds)
        current_region = int(self.env.get_current_region())

        remaining_work = task_duration - self._work_done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.NONE

        self._seen[current_region] += 1
        if has_spot:
            self._avail[current_region] += 1
            self._last_spot_ts[current_region] = elapsed

        # Conservative "need stable" threshold: switch to on-demand and stay there.
        need_stable = time_left <= (remaining_work + (2.0 * restart_overhead + 2.0 * gap))

        # If already on-demand, avoid stopping (prevents thrash and avoids paying overhead repeatedly).
        if last_cluster_type == ClusterType.ON_DEMAND:
            if need_stable:
                return ClusterType.ON_DEMAND
            # Only switch back to spot if there's ample slack to tolerate future outages + overhead.
            slack = time_left - remaining_work
            if has_spot and slack >= (6.0 * restart_overhead + 2.0 * gap) and remaining_work >= (2.0 * gap):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if need_stable:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot and not in stable mode: decide whether to pause.
        # Can we afford to pause one step and still finish via on-demand afterwards?
        can_pause_one = time_left >= (remaining_work + restart_overhead + gap)

        if can_pause_one:
            # While pausing, consider switching regions to improve future spot chances.
            if self._n_regions > 1:
                if (elapsed - self._last_switch_ts) >= self._switch_min_interval:
                    best_r, best_s, cur_s = self._choose_region_to_wait(elapsed, current_region)
                    if best_r != current_region and (best_s - cur_s) >= self._switch_improve_delta:
                        self.env.switch_region(best_r)
                        self._last_switch_ts = elapsed
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
