import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._policy_inited = False
        self._done_cache = 0.0
        self._done_idx = 0
        self._last_progress_elapsed = 0.0

        self._od_mode = False
        self._od_enter_elapsed: Optional[float] = None

        self._obs: List[int] = []
        self._spot: List[int] = []
        self._outage_streak_s: List[float] = []
        self._last_seen_s: List[float] = []
        self._rr_ptr = 0
        self._last_switch_elapsed = -1e30

        self._gap_s = None
        self._soft_buffer_s = None
        self._hard_buffer_s = None
        self._wait_before_od_s = None
        self._exit_od_slack_s = None
        self._min_od_run_s = None
        self._switch_after_outage_s = None
        self._min_switch_interval_s = None

        return self

    @staticmethod
    def _scalar(x) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _ensure_policy_init(self) -> None:
        if self._policy_inited:
            return
        env = self.env
        n = int(env.get_num_regions())
        self._obs = [0] * n
        self._spot = [0] * n
        self._outage_streak_s = [0.0] * n
        self._last_seen_s = [-1e30] * n
        self._rr_ptr = (int(env.get_current_region()) + 1) % n if n > 0 else 0

        self._gap_s = float(getattr(env, "gap_seconds", 3600.0))
        ro = float(getattr(self, "restart_overhead", self._scalar(getattr(self, "restart_overhead_hours", 0.0))))
        if ro <= 0:
            ro = float(self._scalar(getattr(self, "restart_overhead", 0.0)))

        self._hard_buffer_s = max(3600.0, self._gap_s, 5.0 * ro)
        self._soft_buffer_s = max(4.0 * 3600.0, 2.0 * self._gap_s, 10.0 * ro)
        self._wait_before_od_s = max(10.0 * 3600.0, 10.0 * self._gap_s)
        self._exit_od_slack_s = max(12.0 * 3600.0, self._soft_buffer_s + 2.0 * 3600.0)
        self._min_od_run_s = max(2.0 * 3600.0, 4.0 * self._gap_s)
        self._switch_after_outage_s = max(2.0 * self._gap_s, 2.0 * 3600.0)
        self._min_switch_interval_s = self._gap_s

        self._last_progress_elapsed = float(env.elapsed_seconds)
        self._policy_inited = True

    def _update_done_cache(self) -> None:
        tdt = self.task_done_time
        n = len(tdt)
        if n <= self._done_idx:
            return
        inc = 0.0
        for i in range(self._done_idx, n):
            inc += float(tdt[i])
        self._done_idx = n
        if inc > 0.0:
            self._done_cache += inc
            self._last_progress_elapsed = float(self.env.elapsed_seconds)

    def _pick_best_region(self, current: int, now_s: float) -> int:
        n = len(self._obs)
        if n <= 1:
            return current

        best = None
        best_score = -1e18
        best_last_seen = 1e18  # smaller => less recently seen (prefer exploring)
        for i in range(n):
            if i == current:
                continue
            obs = self._obs[i]
            spot = self._spot[i]
            score = (spot + 1.0) / (obs + 2.0)
            last_seen = self._last_seen_s[i]
            if score > best_score + 1e-12:
                best = i
                best_score = score
                best_last_seen = last_seen
            elif abs(score - best_score) <= 1e-12:
                if last_seen < best_last_seen:
                    best = i
                    best_last_seen = last_seen

        if best is None:
            best = (current + 1) % n
        return best

    def _maybe_switch_region(self, has_spot: bool) -> None:
        env = self.env
        n = env.get_num_regions()
        if n <= 1:
            return
        now_s = float(env.elapsed_seconds)
        if now_s - self._last_switch_elapsed < self._min_switch_interval_s:
            return

        cur = int(env.get_current_region())
        if has_spot:
            return

        if self._outage_streak_s[cur] < self._switch_after_outage_s:
            return

        nxt = self._pick_best_region(cur, now_s)
        if nxt != cur:
            env.switch_region(int(nxt))
            self._last_switch_elapsed = now_s

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_policy_init()
        env = self.env
        now_s = float(env.elapsed_seconds)
        gap_s = self._gap_s

        self._update_done_cache()

        cur = int(env.get_current_region())
        self._obs[cur] += 1
        if has_spot:
            self._spot[cur] += 1
            self._outage_streak_s[cur] = 0.0
        else:
            self._outage_streak_s[cur] += gap_s
        self._last_seen_s[cur] = now_s

        task_duration_s = self._scalar(getattr(self, "task_duration", 0.0))
        deadline_s = self._scalar(getattr(self, "deadline", 0.0))
        rem_overhead_s = float(getattr(self, "remaining_restart_overhead", 0.0))

        remaining_work_s = task_duration_s - self._done_cache
        if remaining_work_s <= 0.0:
            return ClusterType.NONE

        time_left_s = deadline_s - now_s
        if time_left_s <= 0.0:
            return ClusterType.NONE

        slack_s = time_left_s - (remaining_work_s + rem_overhead_s)
        no_progress_s = now_s - self._last_progress_elapsed

        mode_hard = slack_s <= self._hard_buffer_s
        mode_soft = (not mode_hard) and (slack_s <= self._soft_buffer_s)

        if mode_hard:
            self._od_mode = True
            if self._od_enter_elapsed is None:
                self._od_enter_elapsed = now_s
        else:
            if not self._od_mode:
                if (not has_spot) and (no_progress_s >= self._wait_before_od_s) and (not mode_soft):
                    self._od_mode = True
                    self._od_enter_elapsed = now_s
            else:
                if (not mode_soft) and (not mode_hard) and has_spot and (slack_s >= self._exit_od_slack_s):
                    if self._od_enter_elapsed is None or (now_s - self._od_enter_elapsed) >= self._min_od_run_s:
                        self._od_mode = False
                        self._od_enter_elapsed = None

        if self._od_mode:
            return ClusterType.ON_DEMAND

        if mode_soft:
            if has_spot and (last_cluster_type == ClusterType.SPOT) and (rem_overhead_s <= 1e-9):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        self._maybe_switch_region(has_spot=False)
        return ClusterType.NONE