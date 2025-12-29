import json
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_aware_multi_region_v1"

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

        self._committed_on_demand: bool = False

        self._done_total: float = 0.0
        self._done_len: int = 0

        self._iter: int = 0
        self._last_switch_iter: int = -10**18
        self._switch_cooldown_steps: Optional[int] = None
        self._ema_avail: Optional[List[float]] = None
        self._ema_alpha: float = 0.10

        return self

    def _ct_none(self):
        if hasattr(ClusterType, "NONE"):
            return ClusterType.NONE
        if hasattr(ClusterType, "None"):
            return getattr(ClusterType, "None")
        if hasattr(ClusterType, "NONE_TYPE"):
            return getattr(ClusterType, "NONE_TYPE")
        return None

    def _update_done_work(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n > self._done_len:
            self._done_total += sum(td[self._done_len:n])
            self._done_len = n
        return self._done_total

    def _init_region_state_if_needed(self) -> None:
        if self._ema_avail is not None:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        self._ema_avail = [0.5] * max(1, n)

    def _maybe_switch_region_when_waiting(self) -> None:
        if self.remaining_restart_overhead and self.remaining_restart_overhead > 0:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            return
        if n <= 1:
            return
        if self._switch_cooldown_steps is None:
            gap = float(getattr(self.env, "gap_seconds", 1.0)) or 1.0
            ro = float(getattr(self, "restart_overhead", 0.0)) or 0.0
            cd = int(round(ro / gap))
            self._switch_cooldown_steps = max(1, cd)

        if (self._iter - self._last_switch_iter) < int(self._switch_cooldown_steps):
            return

        cur = int(self.env.get_current_region())
        ema = self._ema_avail
        if not ema or len(ema) != n:
            self._ema_avail = [0.5] * n
            ema = self._ema_avail

        best = cur
        best_score = -1e18
        for i in range(n):
            s = float(ema[i])
            if i == cur:
                s -= 0.05
            if s > best_score:
                best_score = s
                best = i

        if best == cur:
            best = (cur + 1) % n

        try:
            self.env.switch_region(best)
            self._last_switch_iter = self._iter
        except Exception:
            pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._iter += 1
        self._init_region_state_if_needed()

        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0

        if self._ema_avail is not None and 0 <= cur < len(self._ema_avail):
            v = 1.0 if has_spot else 0.0
            a = self._ema_alpha
            self._ema_avail[cur] = (1.0 - a) * self._ema_avail[cur] + a * v

        done = self._update_done_work()
        task_duration = float(self.task_duration)
        remaining_work = task_duration - done
        ct_none = self._ct_none()

        if remaining_work <= 1e-9:
            return ct_none if ct_none is not None else ClusterType.NONE

        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        remaining_time = deadline - now
        gap = float(getattr(self.env, "gap_seconds", 1.0)) or 1.0
        buffer = gap

        restart_overhead = float(self.restart_overhead)

        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_to_finish = float(self.remaining_restart_overhead or 0.0)
        else:
            overhead_to_finish = restart_overhead

        if self._committed_on_demand:
            if (self.remaining_restart_overhead or 0.0) > 0 and last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if remaining_time - overhead_to_finish <= remaining_work + buffer:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        self._maybe_switch_region_when_waiting()
        return ct_none if ct_none is not None else ClusterType.NONE