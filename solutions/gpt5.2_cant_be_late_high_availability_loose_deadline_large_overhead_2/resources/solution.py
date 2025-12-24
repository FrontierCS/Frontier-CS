import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._inited = False
        self._ema_p = 0.7
        self._ema_alpha = 0.02

        self._prev_has_spot: Optional[bool] = None
        self._run_len = 0
        self._avg_on_steps = 20.0
        self._avg_off_steps = 10.0
        self._run_beta = 0.1

        self._od_lock = False

        self._last_step_idx: Optional[int] = None
        self._est_done_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        self._spec_path = spec_path
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _ensure_init(self):
        if self._inited:
            return
        self._inited = True

        try:
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            gap = 0.0
        if gap > 0:
            self._avg_on_steps = max(self._avg_on_steps, 3600.0 / gap)   # ~1h
            self._avg_off_steps = max(self._avg_off_steps, 1800.0 / gap)  # ~0.5h

    def _update_run_stats(self, has_spot: bool):
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._run_len = 1
            return

        if has_spot == self._prev_has_spot:
            self._run_len += 1
            return

        if self._prev_has_spot:
            self._avg_on_steps = (1.0 - self._run_beta) * self._avg_on_steps + self._run_beta * float(self._run_len)
        else:
            self._avg_off_steps = (1.0 - self._run_beta) * self._avg_off_steps + self._run_beta * float(self._run_len)

        self._prev_has_spot = has_spot
        self._run_len = 1

    def _update_progress_fallback(self, last_cluster_type: ClusterType, has_spot: bool):
        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            return
        if gap <= 0:
            return

        step_idx = int(elapsed // gap) if elapsed >= 0 else 0
        if self._last_step_idx is None:
            self._last_step_idx = step_idx
            self._prev_has_spot = has_spot
            return

        if step_idx > self._last_step_idx:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._est_done_seconds += gap
            elif last_cluster_type == ClusterType.SPOT:
                if self._prev_has_spot is True:
                    self._est_done_seconds += gap
            self._last_step_idx = step_idx

        self._prev_has_spot = has_spot

    def _get_done_work_seconds(self) -> float:
        # Prefer environment-provided progress if available
        for attr in ("task_done_seconds", "done_seconds", "completed_seconds"):
            try:
                v = getattr(self.env, attr, None)
                if isinstance(v, (int, float)) and v >= 0:
                    return float(v)
            except Exception:
                pass

        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return float(self._est_done_seconds)

        try:
            if isinstance(tdt, (int, float)):
                return max(float(tdt), 0.0)
        except Exception:
            pass

        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return float(self._est_done_seconds)

        # If list of tuples (start,end) or (..,duration)
        try:
            if isinstance(tdt[0], (tuple, list)) and len(tdt[0]) >= 2:
                s = 0.0
                for seg in tdt:
                    if not isinstance(seg, (tuple, list)) or len(seg) < 2:
                        continue
                    a = float(seg[0])
                    b = float(seg[1])
                    if b >= a:
                        s += (b - a)
                if s > 0:
                    return s
        except Exception:
            pass

        # If list of numbers: could be per-segment durations OR cumulative progress snapshots.
        try:
            nums = [float(x) for x in tdt if isinstance(x, (int, float))]
            if not nums:
                return float(self._est_done_seconds)

            task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
            s = sum(nums)
            last = nums[-1]
            is_non_decreasing = all(nums[i] <= nums[i + 1] + 1e-9 for i in range(len(nums) - 1))

            # Heuristic: if sum looks too big but last looks plausible, treat as cumulative snapshots.
            if task_duration > 0:
                if is_non_decreasing and (s > task_duration * 1.2) and (0.0 <= last <= task_duration * 1.2):
                    return max(last, 0.0)
                if s <= task_duration * 1.2:
                    return max(s, 0.0)

            # Fallback: pick max if monotonic, else sum
            if is_non_decreasing:
                return max(last, 0.0)
            return max(s, 0.0)
        except Exception:
            return float(self._est_done_seconds)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_progress_fallback(last_cluster_type, has_spot)

        self._ema_p = (1.0 - self._ema_alpha) * self._ema_p + self._ema_alpha * (1.0 if has_spot else 0.0)
        self._update_run_stats(has_spot)

        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            elapsed = 0.0
            gap = 0.0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_work_seconds()
        remaining = max(task_duration - done, 0.0)
        if remaining <= 1e-6:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        # Time buffer for at least one restart + step granularity.
        buffer = restart_overhead + 2.0 * (gap if gap > 0 else 0.0)

        # Slack = time we can afford to be idle from now on (roughly), minus buffer.
        slack = time_left - remaining - buffer

        avg_off_sec = (self._avg_off_steps * gap) if gap > 0 else 3600.0
        avg_off_sec = max(avg_off_sec, gap if gap > 0 else 0.0)

        # Risk threshold: once slack falls below this, lock into on-demand to avoid missing deadline
        # due to a long spot outage near the end.
        risk_thresh = max(3.0 * avg_off_sec, 2.0 * restart_overhead + (gap if gap > 0 else 0.0))
        risk_thresh = min(risk_thresh, 8.0 * 3600.0)  # cap at 8h

        # If we're very close, be more conservative.
        if time_left <= 6.0 * 3600.0:
            risk_thresh = max(risk_thresh, 2.0 * 3600.0)

        if not self._od_lock:
            # If slack is already small, preemptively lock to OD to hedge against future outages.
            if slack <= risk_thresh:
                self._od_lock = True

        if self._od_lock:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot: either idle (NONE) to save cost, or use on-demand to preserve slack.
        # Idle only if slack remains comfortably above risk threshold after idling one step.
        if gap > 0:
            slack_after_idle = (time_left - gap) - remaining - buffer
        else:
            slack_after_idle = slack

        if (slack_after_idle > risk_thresh) and (slack_after_idle >= 0.0):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
