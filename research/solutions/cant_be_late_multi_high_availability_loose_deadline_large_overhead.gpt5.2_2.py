import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _cluster_none() -> ClusterType:
    ct = getattr(ClusterType, "NONE", None)
    if ct is not None:
        return ct
    try:
        return ClusterType["None"]
    except Exception:
        return ClusterType.NONE  # type: ignore[attr-defined]


CT_SPOT = ClusterType.SPOT
CT_OD = ClusterType.ON_DEMAND
CT_NONE = _cluster_none()


class Solution(MultiRegionStrategy):
    NAME = "late_guard_v1"

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

        self._inited = False
        self._committed_on_demand = False

        self._done_work = 0.0
        self._last_task_done_len = 0

        self._spot_true = None
        self._spot_total = None
        self._idle_steps = 0
        self._region_cursor = 0

        self._task_duration_s = None
        self._deadline_s = None
        self._restart_overhead_s = None
        self._gap_s = None
        self._switch_interval = 1
        self._min_obs = 20

        return self

    @staticmethod
    def _scalar(x) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _lazy_init(self) -> None:
        if self._inited:
            return
        n = int(self.env.get_num_regions())
        self._spot_true = [0] * n
        self._spot_total = [0] * n

        self._task_duration_s = self._scalar(self.task_duration)
        self._deadline_s = self._scalar(self.deadline)
        self._restart_overhead_s = self._scalar(self.restart_overhead)
        self._gap_s = float(self.env.gap_seconds)

        gap = self._gap_s if self._gap_s > 0 else 1.0
        self._switch_interval = max(1, int(self._restart_overhead_s / gap) + 1)
        self._min_obs = max(10, int(2 * self._restart_overhead_s / gap) + 1)

        self._inited = True

    def _update_done_work(self) -> None:
        td = self.task_done_time
        new_len = len(td)
        last_len = self._last_task_done_len
        if new_len > last_len:
            s = 0.0
            for i in range(last_len, new_len):
                s += float(td[i])
            self._done_work += s
            self._last_task_done_len = new_len

    def _maybe_switch_region_while_idle(self, current_region: int) -> None:
        if self._spot_total is None or self._spot_true is None:
            return
        if self._idle_steps % self._switch_interval != 0:
            return

        n = len(self._spot_total)
        if n <= 1:
            return

        cand: Optional[int] = None

        start = self._region_cursor % n
        for k in range(n):
            idx = (start + k) % n
            if self._spot_total[idx] < self._min_obs:
                cand = idx
                self._region_cursor = idx + 1
                break

        if cand is None:
            best = current_region
            bt = self._spot_true[best]
            btot = self._spot_total[best]
            best_score = (bt + 1.0) / (btot + 2.0)
            for idx in range(n):
                t = self._spot_true[idx]
                tot = self._spot_total[idx]
                score = (t + 1.0) / (tot + 2.0)
                if score > best_score + 1e-12:
                    best_score = score
                    best = idx
            cand = best

        if cand is not None and cand != current_region:
            try:
                self.env.switch_region(int(cand))
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_work()

        task_duration = self._task_duration_s
        deadline = self._deadline_s
        restart = self._restart_overhead_s
        gap = self._gap_s

        if task_duration is None or deadline is None or restart is None or gap is None:
            return CT_OD if not has_spot else CT_SPOT

        remaining_work = task_duration - self._done_work
        if remaining_work <= 0.0:
            return CT_NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = deadline - elapsed
        if time_left <= 0.0:
            return CT_NONE

        current_region = int(self.env.get_current_region())
        if self._spot_total is not None and self._spot_true is not None:
            if 0 <= current_region < len(self._spot_total):
                self._spot_total[current_region] += 1
                if has_spot:
                    self._spot_true[current_region] += 1

        if self._committed_on_demand or last_cluster_type == CT_OD:
            self._committed_on_demand = True
            self._idle_steps = 0
            return CT_OD

        safety = min(gap, restart)

        if time_left <= remaining_work + restart + safety:
            self._committed_on_demand = True
            self._idle_steps = 0
            return CT_OD

        if has_spot:
            self._idle_steps = 0
            return CT_SPOT

        self._idle_steps += 1
        if time_left - gap >= remaining_work + restart + safety:
            self._maybe_switch_region_while_idle(current_region)
            return CT_NONE

        self._committed_on_demand = True
        self._idle_steps = 0
        return CT_OD