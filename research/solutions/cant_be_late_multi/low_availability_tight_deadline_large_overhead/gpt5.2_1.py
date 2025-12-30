import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        self._num_regions: int = 1
        self._ema: List[float] = []
        self._count: List[int] = []
        self._steps_since_switch: int = 10**9
        self._last_region: Optional[int] = None
        self._down_streak: int = 0

        self._done_sum: float = 0.0
        self._done_len: int = 0

        self._force_ondemand: bool = False
        return self

    def _ensure_init(self) -> None:
        if self._inited:
            return
        self._inited = True
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._ema = [0.5] * self._num_regions
        self._count = [0] * self._num_regions
        try:
            self._last_region = int(self.env.get_current_region())
        except Exception:
            self._last_region = 0
        self._down_streak = 0
        self._steps_since_switch = 10**9

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        L = len(td)
        if L > self._done_len:
            self._done_sum += sum(td[self._done_len : L])
            self._done_len = L

    def _reserve_seconds(self, gap: float) -> float:
        # Keep a conservative reserve slack to avoid deadline miss under poor spot availability.
        return max(0.20 * float(self.task_duration), 6.0 * float(self.restart_overhead), 2.0 * float(gap))

    def _maybe_switch_region(self, current_region: int, slack: float, reserve: float, gap: float) -> None:
        if self._num_regions <= 1:
            return
        if slack <= reserve + 2.0 * gap:
            return
        if self._steps_since_switch < 2:
            return
        if self._down_streak < 2:
            return

        best_idx = current_region
        best_val = -1.0
        for i in range(self._num_regions):
            if i == current_region:
                continue
            v = self._ema[i]
            if v > best_val + 1e-12:
                best_val = v
                best_idx = i

        if best_idx != current_region:
            try:
                self.env.switch_region(best_idx)
                self._steps_since_switch = 0
                self._last_region = best_idx
                self._down_streak = 0
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_done_sum()

        work_done = self._done_sum
        work_rem = float(self.task_duration) - float(work_done)
        if work_rem <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        rem_time = float(self.deadline) - elapsed
        if rem_time <= 0.0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        slack = rem_time - work_rem
        reserve = self._reserve_seconds(gap)

        try:
            region = int(self.env.get_current_region())
        except Exception:
            region = 0

        if self._last_region is None:
            self._last_region = region

        if region != self._last_region:
            self._last_region = region
            self._down_streak = 0

        # Update availability statistics for current region.
        if 0 <= region < self._num_regions:
            c = self._count[region]
            alpha = 0.20 if c < 25 else 0.05
            obs = 1.0 if has_spot else 0.0
            self._ema[region] = (1.0 - alpha) * self._ema[region] + alpha * obs
            self._count[region] = c + 1

        if has_spot:
            self._down_streak = 0
        else:
            self._down_streak += 1

        self._steps_since_switch += 1

        # Update force-on-demand mode (once entered, never leave).
        if not self._force_ondemand:
            if slack <= reserve:
                self._force_ondemand = True
            else:
                if last_cluster_type == ClusterType.ON_DEMAND:
                    t_od = work_rem + float(self.remaining_restart_overhead)
                else:
                    t_od = work_rem + float(self.restart_overhead)
                if rem_time <= t_od + gap:
                    self._force_ondemand = True

        # While overhead is pending, avoid switching cluster types (it can reset the overhead).
        if float(self.remaining_restart_overhead) > 0.0:
            if self._force_ondemand:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            # Otherwise fall through (e.g., spot lost; can't keep SPOT).

        if self._force_ondemand:
            return ClusterType.ON_DEMAND

        # Normal operation: prefer spot when available, but be cautious about switching from on-demand.
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch back to spot if we have ample slack to absorb restart + potential volatility.
                if slack > reserve + float(self.restart_overhead) + gap:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot: either wait (free) or use on-demand if time is getting tight.
        if slack > reserve + gap:
            self._maybe_switch_region(region, slack, reserve, gap)
            return ClusterType.NONE

        return ClusterType.ON_DEMAND