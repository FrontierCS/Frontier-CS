import json
import math
from argparse import Namespace
from typing import List, Optional, Sequence, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


Number = Union[int, float]


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v2"

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

        self._mr_initialized = False
        self._committed_ondemand = False

        self._done_sum = 0.0
        self._done_len = 0

        self._num_regions = 1
        self._spot_obs = []
        self._total_obs = []
        self._no_spot_streak = []

        self._switch_streak = 2
        self._ucb_c = 0.25

        return self

    def _as_scalar(self, x: Union[Number, Sequence[Number]]) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _get_done_list(self) -> List[float]:
        tdt = self.task_done_time
        if isinstance(tdt, (list, tuple)) and tdt and isinstance(tdt[0], (list, tuple)):
            return list(tdt[0])
        return list(tdt) if isinstance(tdt, (list, tuple)) else []

    def _update_done_sum(self) -> None:
        tdt = self.task_done_time
        if isinstance(tdt, (list, tuple)) and tdt and isinstance(tdt[0], (list, tuple)):
            tdt0 = tdt[0]
        else:
            tdt0 = tdt

        if not isinstance(tdt0, (list, tuple)):
            self._done_sum = 0.0
            self._done_len = 0
            return

        n = len(tdt0)
        if n == self._done_len:
            return
        if n < self._done_len:
            self._done_sum = float(sum(float(v) for v in tdt0))
            self._done_len = n
            return

        s = self._done_sum
        for i in range(self._done_len, n):
            s += float(tdt0[i])
        self._done_sum = s
        self._done_len = n

    def _lazy_init(self) -> None:
        if self._mr_initialized:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        n = max(1, n)
        self._num_regions = n
        self._spot_obs = [0] * n
        self._total_obs = [0] * n
        self._no_spot_streak = [0] * n
        self._mr_initialized = True

    def _get_remaining_overhead(self) -> float:
        v = getattr(self, "remaining_restart_overhead", 0.0)
        try:
            return float(v) if v is not None else 0.0
        except Exception:
            return 0.0

    def _work_if_choose(self, choose: ClusterType, last_cluster_type: ClusterType) -> float:
        if choose == ClusterType.NONE:
            return 0.0
        gap = float(self.env.gap_seconds)
        if choose == last_cluster_type:
            overhead = self._get_remaining_overhead()
        else:
            overhead = self._as_scalar(self.restart_overhead)
        w = gap - float(overhead)
        return w if w > 0.0 else 0.0

    def _best_region_ucb(self, current_region: int) -> int:
        n = self._num_regions
        if n <= 1:
            return current_region

        total_all = 0
        for t in self._total_obs:
            total_all += t
        total_all = max(1, total_all)

        best_idx = current_region
        best_score = -1e18

        log_term = math.log(total_all + 1.0)
        c = self._ucb_c

        for i in range(n):
            tot = self._total_obs[i]
            spot = self._spot_obs[i]
            p = (spot + 1.0) / (tot + 2.0)
            bonus = c * math.sqrt(log_term / (tot + 1.0))
            score = p + bonus
            if i == current_region:
                score += 1e-9
            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        duration = self._as_scalar(self.task_duration)
        deadline = self._as_scalar(self.deadline)
        restart_overhead = self._as_scalar(self.restart_overhead)

        remaining_work = duration - self._done_sum
        if remaining_work <= 1e-9:
            self._committed_ondemand = False
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = deadline - elapsed
        gap = float(self.env.gap_seconds)

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        cur_region = max(0, min(self._num_regions - 1, cur_region))

        self._total_obs[cur_region] += 1
        if has_spot:
            self._spot_obs[cur_region] += 1
            self._no_spot_streak[cur_region] = 0
        else:
            self._no_spot_streak[cur_region] += 1

        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        time_left_after_step = time_left - gap

        safe_to_wait_one_step = (time_left_after_step >= 0.0) and (remaining_work + restart_overhead <= time_left_after_step)

        safe_to_take_spot_step = False
        if has_spot and time_left_after_step >= 0.0:
            spot_work_now = self._work_if_choose(ClusterType.SPOT, last_cluster_type)
            rem_after_spot = remaining_work - spot_work_now
            if rem_after_spot < 0.0:
                rem_after_spot = 0.0
            safe_to_take_spot_step = (rem_after_spot + restart_overhead <= time_left_after_step)

        if not safe_to_wait_one_step:
            if has_spot and safe_to_take_spot_step:
                return ClusterType.SPOT
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if self._no_spot_streak[cur_region] >= self._switch_streak and self._num_regions > 1:
            best = self._best_region_ucb(cur_region)
            if best != cur_region:
                try:
                    self.env.switch_region(best)
                except Exception:
                    pass

        return ClusterType.NONE
