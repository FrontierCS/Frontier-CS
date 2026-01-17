import json
from argparse import Namespace
from typing import List, Optional

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

        self._initialized = False
        self._done_work = 0.0
        self._last_done_len = 0

        self._step_num = 0
        self._locked_od = False

        self._gap = None
        self._n_regions = None

        self._spot_total: List[int] = []
        self._spot_avail: List[int] = []
        self._spot_down_streak: List[int] = []

        self._total_wait_steps = 0
        self._consec_wait_steps = 0

        self._last_switch_step = -10**18
        self._od_hold_steps = 0

        # Tunables (in seconds)
        self._max_consec_wait_seconds = 3.0 * 3600.0
        self._max_total_wait_seconds = 12.0 * 3600.0
        self._min_slack_to_wait_seconds = 2.0 * 3600.0
        self._switch_cooldown_seconds = 1.0 * 3600.0
        self._switch_after_down_seconds = 1.0 * 3600.0
        self._od_hold_seconds = 0.5 * 3600.0

        # Ratios
        self._lock_od_ratio_threshold = 1.08  # remaining_time / (remaining_work + overhead)
        self._prefer_wait_ratio_threshold = 1.25

        return self

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._gap = float(self.env.gap_seconds)
        self._n_regions = int(self.env.get_num_regions())

        self._spot_total = [0] * self._n_regions
        self._spot_avail = [0] * self._n_regions
        self._spot_down_streak = [0] * self._n_regions

        def steps_from_seconds(x: float) -> int:
            if self._gap <= 0:
                return 1
            return max(1, int(x / self._gap + 1e-9))

        self._max_consec_wait_steps = steps_from_seconds(self._max_consec_wait_seconds)
        self._max_total_wait_steps = steps_from_seconds(self._max_total_wait_seconds)
        self._switch_cooldown_steps = steps_from_seconds(self._switch_cooldown_seconds)
        self._switch_after_down_steps = steps_from_seconds(self._switch_after_down_seconds)
        self._od_hold_steps_cfg = steps_from_seconds(self._od_hold_seconds)

        self._initialized = True

    def _update_done_work(self) -> None:
        l = len(self.task_done_time)
        if l > self._last_done_len:
            self._done_work += sum(self.task_done_time[self._last_done_len:l])
            self._last_done_len = l

    def _region_score(self, idx: int) -> float:
        # Smoothed availability estimate
        a = self._spot_avail[idx]
        t = self._spot_total[idx]
        return (a + 1.0) / (t + 2.0)

    def _pick_best_region(self, exclude: Optional[int] = None) -> int:
        if self._n_regions <= 1:
            return 0
        best_idx = 0 if exclude != 0 else 1
        best_score = self._region_score(best_idx)
        for i in range(self._n_regions):
            if exclude is not None and i == exclude:
                continue
            s = self._region_score(i)
            if s > best_score + 1e-12:
                best_score = s
                best_idx = i
        return best_idx

    def _should_lock_od(self, remaining_time: float, remaining_work: float) -> bool:
        if remaining_work <= 0:
            return False
        # Conservative: assume at least one restart overhead may be needed.
        denom = remaining_work + max(self.restart_overhead, self.remaining_restart_overhead)
        if denom <= 0:
            return False
        ratio = remaining_time / denom
        if ratio <= self._lock_od_ratio_threshold:
            return True
        # Extra conservative margin in steps to handle discretization / bad luck.
        margin = self.restart_overhead + 2.0 * float(self.env.gap_seconds)
        return remaining_time <= (remaining_work + margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_done_work()
        self._step_num += 1

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline - elapsed)
        remaining_work = float(self.task_duration - self._done_work)

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if remaining_time <= 0:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        cur_region = int(self.env.get_current_region())
        self._spot_total[cur_region] += 1
        if has_spot:
            self._spot_avail[cur_region] += 1
            self._spot_down_streak[cur_region] = 0
        else:
            self._spot_down_streak[cur_region] += 1

        if not self._locked_od and self._should_lock_od(remaining_time, remaining_work):
            self._locked_od = True
            self._od_hold_steps = 0

        if self._locked_od:
            return ClusterType.ON_DEMAND

        # Hysteresis: if we recently chose on-demand (non-locked), keep it briefly.
        if last_cluster_type == ClusterType.ON_DEMAND and self._od_hold_steps > 0:
            self._od_hold_steps -= 1
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work
        denom = remaining_work + 1e-9
        ratio = remaining_time / denom

        if has_spot:
            self._consec_wait_steps = 0
            return ClusterType.SPOT

        # Spot unavailable in current region.
        # Consider switching regions during downtime.
        if (
            self._n_regions > 1
            and self._spot_down_streak[cur_region] >= self._switch_after_down_steps
            and (self._step_num - self._last_switch_step) >= self._switch_cooldown_steps
        ):
            best = self._pick_best_region(exclude=cur_region)
            if best != cur_region:
                self.env.switch_region(best)
                self._last_switch_step = self._step_num
                cur_region = best

        # Decide whether to wait (NONE) or pay for on-demand.
        can_wait = (
            slack >= self._min_slack_to_wait_seconds
            and ratio >= self._prefer_wait_ratio_threshold
            and self._total_wait_steps < self._max_total_wait_steps
            and self._consec_wait_steps < self._max_consec_wait_steps
        )

        if can_wait:
            self._total_wait_steps += 1
            self._consec_wait_steps += 1
            return ClusterType.NONE

        self._consec_wait_steps = 0
        self._od_hold_steps = self._od_hold_steps_cfg
        return ClusterType.ON_DEMAND