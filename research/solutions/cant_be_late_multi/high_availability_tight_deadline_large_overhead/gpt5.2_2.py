import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_switcher_v1"

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

    def _lazy_init(self) -> None:
        if getattr(self, "_inited", False):
            return
        self._inited = True

        self._CT_SPOT = ClusterType.SPOT
        self._CT_OD = ClusterType.ON_DEMAND
        self._CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))
        if self._CT_NONE is None:
            self._CT_NONE = ClusterType.NONE  # type: ignore[attr-defined]

        try:
            self._n_regions = int(self.env.get_num_regions())
        except Exception:
            self._n_regions = 1

        self._alpha = 0.02
        self._p: List[float] = [0.85] * self._n_regions
        self._obs_count: List[int] = [0] * self._n_regions
        self._last_seen_spot: List[float] = [-1.0] * self._n_regions
        self._last_seen_nospot: List[float] = [-1.0] * self._n_regions

        self._mode = 0  # 0: spot_preferred, 1: on_demand_temp, 2: on_demand_commit
        self._no_spot_streak = 0
        self._last_switch_time = -1e30

        self._td_len = 0
        self._done_sum = 0.0

        self._switch_streak = 1
        self._switch_cooldown_seconds = 0.0

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l == self._td_len:
            return
        for i in range(self._td_len, l):
            self._done_sum += float(td[i])
        self._td_len = l

    def _compute_region_switch_params(self) -> None:
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        overhead = float(self.restart_overhead)
        if gap <= 0:
            gap = 1.0

        # Wait at least ~half an overhead before switching, in steps
        self._switch_streak = max(1, int((0.5 * overhead) / gap))
        # Don't switch too often, in seconds
        self._switch_cooldown_seconds = max(1.5 * overhead, 10.0 * gap)

    def _maybe_switch_region(self, elapsed: float, cur_region: int) -> None:
        if self._n_regions <= 1:
            return
        if self._no_spot_streak < self._switch_streak:
            return
        if elapsed - self._last_switch_time < self._switch_cooldown_seconds:
            return

        best = cur_region
        best_score = -1e18
        # recency window: 6 hours
        recency_window = 6.0 * 3600.0

        for i in range(self._n_regions):
            if i == cur_region:
                continue
            score = self._p[i]
            last = self._last_seen_spot[i]
            if last >= 0.0:
                dt = elapsed - last
                if dt <= recency_window:
                    score += 0.10 * (1.0 - (dt / recency_window))
            else:
                score += 0.02
            if score > best_score:
                best_score = score
                best = i

        if best != cur_region:
            try:
                self.env.switch_region(best)
                self._last_switch_time = elapsed
                self._no_spot_streak = 0
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        work_left = float(self.task_duration) - float(self._done_sum)
        if work_left <= 0.0:
            return self._CT_NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(self.deadline)
        time_left = deadline - elapsed

        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0
        overhead = float(self.restart_overhead)

        if self._switch_cooldown_seconds <= 0.0:
            self._compute_region_switch_params()

        # Update region availability statistics
        try:
            r = int(self.env.get_current_region())
        except Exception:
            r = 0

        if 0 <= r < self._n_regions:
            self._obs_count[r] += 1
            x = 1.0 if has_spot else 0.0
            p_old = self._p[r]
            self._p[r] = (1.0 - self._alpha) * p_old + self._alpha * x
            if has_spot:
                self._last_seen_spot[r] = elapsed
            else:
                self._last_seen_nospot[r] = elapsed

        if has_spot:
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        # Slack (time minus required pure work time)
        slack = time_left - work_left

        # Conservative commitment logic
        if last_cluster_type == self._CT_OD:
            overhead_future_od = float(getattr(self, "remaining_restart_overhead", 0.0))
        else:
            overhead_future_od = overhead

        # Safety buffer to prevent deadline misses due to discretization/overhead effects
        safety = max(2.0 * gap, 0.5 * overhead)

        # If it's time-critical, commit to on-demand until finish
        if time_left <= (work_left + overhead_future_od + safety):
            self._mode = 2
        if self._mode == 2:
            return self._CT_OD

        # On-demand temporary mode: revert to spot only if we have ample slack
        if self._mode == 1:
            if has_spot:
                revert_need = overhead + safety + 2.0 * gap
                if slack > revert_need:
                    self._mode = 0
                    return self._CT_SPOT
            return self._CT_OD

        # Spot preferred mode
        if has_spot:
            return self._CT_SPOT

        # No spot: decide between waiting (NONE) and starting on-demand temporarily
        start_od_slack = max(6.0 * overhead, 10.0 * gap)
        if slack <= start_od_slack:
            self._mode = 1
            return self._CT_OD

        # Otherwise wait for spot; optionally switch region to improve chances
        if 0 <= r < self._n_regions:
            self._maybe_switch_region(elapsed, r)
        return self._CT_NONE