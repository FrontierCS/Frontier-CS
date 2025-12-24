import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._inited = False
        self._committed_on_demand = False
        self._done_total = 0.0
        self._done_len = 0
        self._t_obs = 0
        self._avail_counts = []
        self._total_counts = []
        self._consec_no_spot = 0
        self._gap = None
        return self

    def _ensure_init(self) -> None:
        if self._inited:
            return
        n = int(self.env.get_num_regions())
        self._avail_counts = [0] * n
        self._total_counts = [0] * n
        self._gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        self._inited = True

    @staticmethod
    def _as_float(x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_done_total(self) -> None:
        td = self.task_done_time
        if td is None:
            self._done_total = 0.0
            self._done_len = 0
            return
        cur_len = len(td)
        if cur_len == self._done_len:
            return
        s = 0.0
        for i in range(self._done_len, cur_len):
            s += float(td[i])
        self._done_total += s
        self._done_len = cur_len

    def _best_p(self) -> float:
        alpha = 1.0
        best = 0.0
        for a, t in zip(self._avail_counts, self._total_counts):
            p = (a + alpha) / (t + 2.0 * alpha)
            if p > best:
                best = p
        return best if best > 0.0 else 0.7

    def _reserve_time(self) -> float:
        task_dur = self._as_float(self.task_duration)
        base = max(3.0 * self._as_float(self.restart_overhead), 1800.0)  # at least 30 min
        best_p = self._best_p()
        extra = max(0.0, (0.95 - best_p)) * task_dur * 0.5
        reserve = base + extra
        reserve = min(reserve, 6.0 * 3600.0)
        return reserve

    def _need_time_if_start_on_demand(self, last_cluster_type: ClusterType, remaining_work: float) -> float:
        ro = self._as_float(self.restart_overhead)
        rro = self._as_float(self.remaining_restart_overhead)
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead = rro
        else:
            overhead = ro
        return remaining_work + overhead

    def _select_next_region_to_probe(self, current_region: int) -> Optional[int]:
        n = len(self._total_counts)
        if n <= 1:
            return None

        for i in range(n):
            if i != current_region and self._total_counts[i] == 0:
                return i

        alpha = 1.0
        total_obs = max(self._t_obs, 1)
        ln = math.log(total_obs + 1.0)
        best_idx = None
        best_score = -1e9
        for i in range(n):
            if i == current_region:
                continue
            a = self._avail_counts[i]
            t = self._total_counts[i]
            p = (a + alpha) / (t + 2.0 * alpha)
            bonus = 0.15 * math.sqrt(ln / (t + 1.0))
            score = p + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_done_total()

        task_dur = self._as_float(self.task_duration)
        deadline = self._as_float(self.deadline)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        remaining_work = task_dur - self._done_total
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        region = int(self.env.get_current_region())
        if 0 <= region < len(self._total_counts):
            self._total_counts[region] += 1
            if has_spot:
                self._avail_counts[region] += 1
            self._t_obs += 1

        reserve = self._reserve_time()
        need_od = self._need_time_if_start_on_demand(last_cluster_type, remaining_work)
        should_force_od = remaining_time <= (need_od + reserve)

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        if should_force_od:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            self._consec_no_spot = 0
            return ClusterType.SPOT

        self._consec_no_spot += 1

        target = self._select_next_region_to_probe(region)
        if target is not None and target != region:
            self.env.switch_region(int(target))

        return ClusterType.NONE
