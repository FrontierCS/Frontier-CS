import json
import math
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_spot_v1"

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
        return self

    @staticmethod
    def _to_scalar(x: object) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _init_state_if_needed(self) -> None:
        if getattr(self, "_mr_inited", False):
            return
        self._mr_inited = True

        self._force_ondemand = False
        self._done_work = 0.0
        self._last_done_len = 0

        self._miss_streak = 0
        self._t = 0

        n = int(self.env.get_num_regions())
        self._region_total = [0] * n
        self._region_avail = [0] * n

        self.task_duration = self._to_scalar(getattr(self, "task_duration", 0.0))
        self.deadline = self._to_scalar(getattr(self, "deadline", 0.0))
        self.restart_overhead = self._to_scalar(getattr(self, "restart_overhead", 0.0))

    def _update_done_work(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l > self._last_done_len:
            self._done_work += sum(td[self._last_done_len : l])
            self._last_done_len = l

    def _maybe_switch_region_while_waiting(self) -> None:
        n = int(self.env.get_num_regions())
        if n <= 1:
            return
        curr = int(self.env.get_current_region())

        # Optimistic/UCB-like score: favor untried regions while still preferring proven ones.
        best_idx: Optional[int] = None
        best_score = -1e18

        logt = math.log(self._t + 2.0)
        for i in range(n):
            if i == curr:
                continue
            tot = self._region_total[i]
            if tot <= 0:
                score = 1.0 + 0.5  # strongly optimistic for untried
            else:
                p = self._region_avail[i] / tot
                score = p + 0.35 * math.sqrt(logt / tot)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx is not None and best_idx != curr:
            self.env.switch_region(int(best_idx))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_state_if_needed()
        self._t += 1

        self._update_done_work()

        remaining_work = self.task_duration - self._done_work
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)

        region = int(self.env.get_current_region())
        if 0 <= region < len(self._region_total):
            self._region_total[region] += 1
            if has_spot:
                self._region_avail[region] += 1

        if has_spot:
            self._miss_streak = 0
        else:
            self._miss_streak += 1

        # Safety margin: enough to avoid missing deadline due to one extra restart, plus a small timestep fuzz.
        safety = 2.0 * self.restart_overhead + min(600.0, 0.1 * gap)

        # If we commit to on-demand now, assume at most one restart overhead if not already on-demand.
        start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        latest_finish_if_ondemand_now = elapsed + remaining_work + start_overhead

        if self._force_ondemand or (latest_finish_if_ondemand_now + safety >= self.deadline):
            self._force_ondemand = True
            return ClusterType.ON_DEMAND

        # Spot-first behavior when not forced.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide wait vs on-demand.
        latest_finish_if_wait_then_ondemand = elapsed + gap + remaining_work + self.restart_overhead
        if latest_finish_if_wait_then_ondemand + safety < self.deadline:
            self._maybe_switch_region_while_waiting()
            return ClusterType.NONE

        self._force_ondemand = True
        return ClusterType.ON_DEMAND