import json
import math
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_aware_multiregion_v1"

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

        # Normalize potential list attributes to scalars for convenience/safety.
        if isinstance(getattr(self, "task_duration", None), (list, tuple)):
            self.task_duration = float(self.task_duration[0])
        if isinstance(getattr(self, "restart_overhead", None), (list, tuple)):
            self.restart_overhead = float(self.restart_overhead[0])
        if isinstance(getattr(self, "deadline", None), (list, tuple)):
            self.deadline = float(self.deadline[0])

        # Lazy-init in _step (env not guaranteed set here).
        self._inited = False
        return self

    def _lazy_init(self) -> None:
        n = int(self.env.get_num_regions())
        self._num_regions = n
        self._t_obs = 0
        self._n_vis = [0] * n
        self._n_spot = [0] * n

        self._last_region: Optional[int] = None
        self._no_spot_streak = 0

        self._work_done = 0.0
        self._done_len = 0

        self._emergency = False

        gap = float(self.env.gap_seconds)
        # Switch heuristic parameters (in steps).
        self._switch_threshold_steps = max(2, int(math.ceil(3600.0 / max(gap, 1e-9))))  # ~1 hour
        self._min_switch_interval_steps = max(1, self._switch_threshold_steps // 2)
        self._last_switch_step = -10**18

        # UCB coefficient (small; we don't want to thrash).
        self._ucb_c = 0.35

        self._inited = True

    def _update_work_done(self) -> None:
        td = self.task_done_time
        ln = len(td)
        if ln > self._done_len:
            s = 0.0
            for i in range(self._done_len, ln):
                s += float(td[i])
            self._work_done += s
            self._done_len = ln

    def _current_step_index(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return int(self.env.elapsed_seconds)
        return int(self.env.elapsed_seconds // gap)

    def _best_region_ucb(self, exclude_region: Optional[int] = None) -> int:
        # Deterministic UCB1-style score with Beta(1,1) mean smoothing.
        t = max(1, self._t_obs)
        logt = math.log(t + 1.0)
        best_idx = 0
        best_score = -1e18
        for i in range(self._num_regions):
            if exclude_region is not None and i == exclude_region:
                continue
            n = self._n_vis[i]
            s = self._n_spot[i]
            mean = (s + 1.0) / (n + 2.0)
            bonus = self._ucb_c * math.sqrt(logt / (n + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._inited:
            self._lazy_init()

        self._update_work_done()

        now = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - now
        work_left = float(self.task_duration) - float(self._work_done)

        if work_left <= 1e-9:
            return ClusterType.NONE

        if time_left <= 0.0:
            return ClusterType.NONE

        rid = int(self.env.get_current_region())
        if self._last_region is None or rid != self._last_region:
            self._no_spot_streak = 0
            self._last_region = rid

        # Update region spot stats.
        self._t_obs += 1
        self._n_vis[rid] += 1
        if has_spot:
            self._n_spot[rid] += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        gap = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)

        # Enter emergency mode when we're close enough to the deadline that waiting risks missing it.
        # Conservative buffer to accommodate discretization and restart overhead dynamics.
        emergency_margin = ro + 4.0 * gap
        if (not self._emergency) and (time_left <= work_left + emergency_margin):
            self._emergency = True

        if self._emergency:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot: wait (NONE). Optionally switch regions (while idle) to improve chances next step.
        # Avoid switching too frequently; avoid switching while a restart overhead is still pending.
        cur_step = self._current_step_index()
        try:
            pending_overhead = float(self.remaining_restart_overhead)
        except Exception:
            pending_overhead = 0.0

        can_switch = (
            cur_step - self._last_switch_step >= self._min_switch_interval_steps
            and pending_overhead <= 1e-9
        )

        # Only switch after observing sustained unavailability, or early exploration.
        if can_switch:
            explore_phase = self._t_obs < max(8, 2 * self._num_regions)
            if explore_phase or (self._no_spot_streak >= self._switch_threshold_steps):
                new_region = self._best_region_ucb(exclude_region=rid)
                if new_region != rid:
                    self.env.switch_region(new_region)
                    self._last_switch_step = cur_step
                    self._no_spot_streak = 0
                    self._last_region = new_region

        return ClusterType.NONE
