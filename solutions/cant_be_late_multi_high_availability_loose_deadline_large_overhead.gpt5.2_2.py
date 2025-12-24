import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _cluster_none() -> ClusterType:
    if hasattr(ClusterType, "NONE"):
        return ClusterType.NONE
    return getattr(ClusterType, "None")


_CT_NONE = _cluster_none()


class Solution(MultiRegionStrategy):
    NAME = "adaptive_spot_wait_v1"

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
        self._init_internal_state()
        return self

    def _init_internal_state(self) -> None:
        self._inited = False
        self._step_count = 0
        self._cached_done = 0.0
        self._cached_done_len = 0

        self._scores: Optional[List[float]] = None
        self._seen: Optional[List[int]] = None
        self._last_region_switch_step = -10**9
        self._switch_cooldown_steps = 2
        self._unavail_streak = 0

        self._ewma_alpha = 0.06  # ~16-step half-life

    def _ensure_inited(self) -> None:
        if self._inited:
            return
        n = int(self.env.get_num_regions())
        if n <= 0:
            n = 1
        self._scores = [0.5] * n
        self._seen = [0] * n
        self._inited = True

    def _update_done_cache(self) -> float:
        tdt = self.task_done_time
        ln = len(tdt)
        if ln != self._cached_done_len:
            if ln > self._cached_done_len:
                add = 0.0
                for i in range(self._cached_done_len, ln):
                    add += float(tdt[i])
                self._cached_done += add
            else:
                # Shouldn't happen, but keep consistent.
                self._cached_done = 0.0
                for v in tdt:
                    self._cached_done += float(v)
            self._cached_done_len = ln
        return self._cached_done

    def _best_region(self, cur: int) -> int:
        scores = self._scores
        if not scores:
            return cur
        best = cur
        best_score = scores[cur]
        for i, s in enumerate(scores):
            if i != cur and s > best_score + 1e-12:
                best_score = s
                best = i
        return best

    def _maybe_switch_region_when_idle(self, cur_region: int) -> None:
        if (self._step_count - self._last_region_switch_step) < self._switch_cooldown_steps:
            return
        target = self._best_region(cur_region)
        if target != cur_region:
            self.env.switch_region(int(target))
            self._last_region_switch_step = self._step_count
            self._unavail_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_inited()
        self._step_count += 1

        cur_region = int(self.env.get_current_region())
        if cur_region < 0:
            cur_region = 0
        if self._scores is not None and cur_region >= len(self._scores):
            # Defensive: resize if env reports more regions than initial.
            n = int(self.env.get_num_regions())
            if n > len(self._scores):
                self._scores.extend([0.5] * (n - len(self._scores)))
                self._seen.extend([0] * (n - len(self._seen)))

        if self._scores is not None:
            a = self._ewma_alpha
            self._scores[cur_region] = (1.0 - a) * self._scores[cur_region] + a * (1.0 if has_spot else 0.0)
            self._seen[cur_region] += 1

        done = self._update_done_cache()
        remaining_work = float(self.task_duration) - float(done)
        if remaining_work <= 0.0:
            return _CT_NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work
        gap = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)

        # Conservative "finish-guarantee" phase: use on-demand near the end.
        critical_slack = 2.0 * gap
        if slack <= critical_slack:
            return ClusterType.ON_DEMAND

        if has_spot:
            self._unavail_streak = 0
            return ClusterType.SPOT

        self._unavail_streak += 1

        # If we can afford to idle one step, wait for spot (and reposition to a better region).
        idle_threshold = gap + ro
        if slack >= idle_threshold:
            if self._unavail_streak >= 1:
                self._maybe_switch_region_when_idle(cur_region)
            return _CT_NONE

        # Not enough slack to wait: pay on-demand for progress.
        return ClusterType.ON_DEMAND
