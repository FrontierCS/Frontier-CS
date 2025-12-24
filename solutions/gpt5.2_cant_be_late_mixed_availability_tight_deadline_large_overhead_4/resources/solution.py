import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._p_ema = 0.7
        self._ema_outage = 1800.0  # seconds
        self._unavail_streak = 0.0
        self._spot_stable_steps = 0
        self._commit_od = False

        self._last_has_spot: Optional[bool] = None
        self._od_run_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        lst = getattr(self, "task_done_time", None)
        if lst is None:
            return 0.0
        if isinstance(lst, (int, float)):
            done = float(lst)
            if dur > 0:
                done = min(done, dur)
            return max(0.0, done)
        try:
            seq = list(lst)
        except Exception:
            return 0.0
        if not seq:
            return 0.0
        try:
            s = float(sum(seq))
            m = float(max(seq))
        except Exception:
            return 0.0

        # Heuristic to handle either "segments" or "cumulative" formats.
        if dur > 0 and s > dur * 1.2:
            done = m
        else:
            done = s
        if dur > 0:
            done = min(done, dur)
        return max(0.0, done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._get_done_seconds()
        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)
        slack_remaining = remaining_time - remaining_work

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Update on-demand run time (based on previous step choice).
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_run_seconds += gap
        else:
            self._od_run_seconds = 0.0

        # Update spot availability EMA and outage statistics.
        alpha = 0.01
        self._p_ema = (1.0 - alpha) * self._p_ema + alpha * (1.0 if has_spot else 0.0)
        self._p_ema = min(0.999, max(0.001, self._p_ema))

        if self._last_has_spot is False and has_spot is True and self._unavail_streak > 0.0:
            beta = 0.2
            self._ema_outage = (1.0 - beta) * self._ema_outage + beta * self._unavail_streak
            self._ema_outage = max(gap, min(self._ema_outage, 12.0 * 3600.0))
            self._unavail_streak = 0.0

        if has_spot:
            self._spot_stable_steps += 1
        else:
            self._spot_stable_steps = 0
            self._unavail_streak += gap

        self._last_has_spot = has_spot

        # Dynamic buffers
        base_reserve = 900.0  # 15 minutes
        reserve = base_reserve + (1.0 - self._p_ema) * 5400.0  # up to +1.5h
        end_buffer = max(2.0 * gap, 600.0)  # at least 10 minutes
        commit_slack = restart_overhead + 2.0 * gap + 900.0 + (1.0 - self._p_ema) * 3600.0

        # Hard-commit to on-demand when slack is low.
        if (not self._commit_od) and (slack_remaining <= commit_slack or remaining_time <= remaining_work + restart_overhead + end_buffer):
            self._commit_od = True

        if self._commit_od:
            if has_spot is False:
                return ClusterType.ON_DEMAND
            # If already on OD, keep it. Otherwise switching to OD costs overhead too,
            # but when committed we always choose OD to guarantee completion.
            return ClusterType.ON_DEMAND

        # Not committed: use spot when available; decide what to do during outages.
        if not has_spot:
            # Estimate remaining outage duration and decide whether we can afford to wait.
            remaining_outage_est = max(0.0, self._ema_outage - self._unavail_streak)
            # If we can afford waiting out the expected remainder plus a reserve, pause.
            if slack_remaining > remaining_outage_est + reserve:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Spot is available and not committed.
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Revert to spot only if spot seems stable and we have enough slack for the switch overhead.
            stable_required = max(2, int(math.ceil(900.0 / max(gap, 1.0))))  # ~15 minutes
            revert_slack_needed = reserve + 2.0 * restart_overhead + 2.0 * gap
            if (
                self._spot_stable_steps >= stable_required
                and slack_remaining >= revert_slack_needed
                and remaining_work >= 3.0 * 3600.0
                and self._od_run_seconds >= 900.0
            ):
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
