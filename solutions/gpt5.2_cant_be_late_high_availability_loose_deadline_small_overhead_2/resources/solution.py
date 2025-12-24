import math
from typing import Optional, Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._initialized = False

        self._prev_has_spot: Optional[bool] = None
        self._run_elapsed: float = 0.0
        self._down_elapsed: float = 0.0

        self._total_steps: int = 0
        self._avail_steps: int = 0

        self._ema_down: float = 1800.0  # seconds
        self._ema_up: float = 7200.0    # seconds
        self._ema_alpha: float = 0.2

        self._locked_od: bool = False
        self._od_since: Optional[float] = None

        self._last_work_done: Optional[float] = None
        self._last_returned: ClusterType = ClusterType.NONE
        self._zero_progress_streak: int = 0

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        return self

    @staticmethod
    def _is_od(ct: ClusterType) -> bool:
        return ct == ClusterType.ON_DEMAND

    @staticmethod
    def _is_spot(ct: ClusterType) -> bool:
        return ct == ClusterType.SPOT

    @staticmethod
    def _is_none(ct: ClusterType) -> bool:
        return ct == ClusterType.NONE

    def _get_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        try:
            last = tdt[-1]
        except Exception:
            return 0.0

        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)

        def is_num(x):
            return isinstance(x, (int, float)) and not isinstance(x, bool)

        if is_num(last):
            n = len(tdt)
            # If it looks like cumulative non-decreasing progress, use last element.
            if n >= 2 and all(is_num(x) for x in tdt[max(0, n - 5):n]):
                nondec = True
                for i in range(max(1, n - 5), n):
                    if float(tdt[i]) < float(tdt[i - 1]) - 1e-9:
                        nondec = False
                        break
                if nondec and float(last) <= task_dur * 1.05:
                    return float(last)

            # Otherwise, treat as list of segment durations and sum.
            s = 0.0
            for x in tdt:
                if is_num(x):
                    s += float(x)
                elif isinstance(x, (tuple, list)) and len(x) == 2 and is_num(x[0]) and is_num(x[1]):
                    s += float(x[1]) - float(x[0])
            return s

        if isinstance(last, (tuple, list)) and len(last) == 2:
            s = 0.0
            for seg in tdt:
                if isinstance(seg, (tuple, list)) and len(seg) == 2 and is_num(seg[0]) and is_num(seg[1]):
                    s += float(seg[1]) - float(seg[0])
                elif is_num(seg):
                    s += float(seg)
            return s

        return 0.0

    def _update_spot_stats(self, has_spot: bool) -> None:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0.0:
            gap = 1.0

        self._total_steps += 1
        if has_spot:
            self._avail_steps += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._run_elapsed = gap
            self._down_elapsed = gap if not has_spot else 0.0
            return

        if has_spot == self._prev_has_spot:
            self._run_elapsed += gap
        else:
            # Run ended; update EMA for the run that ended.
            if self._prev_has_spot:
                self._ema_up = (1.0 - self._ema_alpha) * self._ema_up + self._ema_alpha * self._run_elapsed
            else:
                self._ema_down = (1.0 - self._ema_alpha) * self._ema_down + self._ema_alpha * self._run_elapsed
            self._prev_has_spot = has_spot
            self._run_elapsed = gap

        self._down_elapsed = self._run_elapsed if (self._prev_has_spot is False) else 0.0

    def _detect_overhead(self, last_cluster_type: ClusterType) -> bool:
        work_done = self._get_work_done()
        in_overhead = False
        if self._last_work_done is not None:
            delta = work_done - self._last_work_done
            remaining = max(0.0, float(getattr(self, "task_duration", 0.0) or 0.0) - work_done)
            if remaining > 1e-6 and self._last_returned in (ClusterType.SPOT, ClusterType.ON_DEMAND) and delta <= 1e-9:
                self._zero_progress_streak += 1
            else:
                self._zero_progress_streak = 0
        self._last_work_done = work_done

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0.0:
            gap = 1.0
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        expected_overhead_steps = max(1, int(math.ceil(max(ro, 1e-9) / gap)))

        if self._zero_progress_streak > 0 and self._zero_progress_streak <= expected_overhead_steps + 1:
            in_overhead = True

        return in_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._initialized = True

        self._update_spot_stats(has_spot)
        in_overhead = self._detect_overhead(last_cluster_type)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0.0:
            gap = 1.0

        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        work_done = self._get_work_done()
        remaining_work = max(0.0, task_dur - work_done)

        if remaining_work <= 1e-6:
            self._last_returned = ClusterType.NONE
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        if time_remaining <= 0.0:
            self._locked_od = True
            self._last_returned = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # If overhead is currently being paid, avoid switching clusters (resets overhead).
        if in_overhead:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._last_returned = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._last_returned = ClusterType.SPOT
                return ClusterType.SPOT

        overhead_to_od = ro if last_cluster_type != ClusterType.ON_DEMAND else 0.0
        hard_safety = max(2.0 * gap, 0.5 * ro)
        hard_mode = time_remaining <= (remaining_work + overhead_to_od + hard_safety)

        if hard_mode:
            self._locked_od = True

        if self._locked_od:
            if self._od_since is None:
                self._od_since = elapsed
            self._last_returned = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Soft decision mode (try to maximize spot usage while keeping enough slack).
        slack_remaining = time_remaining - remaining_work  # time we can afford to not make progress

        avail_rate = (self._avail_steps + 1.0) / (self._total_steps + 2.0)
        # Higher required slack to switch back to spot when observed availability is lower.
        switchback_slack = max(1800.0, (1.0 - avail_rate) * 6.0 * 3600.0 + 1800.0)

        od_min_run = max(900.0, 0.25 * 3600.0)  # 15 minutes minimum OD run
        soft_buffer = max(ro, 2.0 * gap)

        if has_spot:
            # If we're currently on OD, optionally switch back to spot if there's ample slack.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._od_since is None:
                    self._od_since = elapsed
                od_run = elapsed - self._od_since
                if od_run < od_min_run:
                    self._last_returned = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
                if slack_remaining > switchback_slack:
                    self._od_since = None
                    self._last_returned = ClusterType.SPOT
                    return ClusterType.SPOT
                self._last_returned = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND

            self._od_since = None
            self._last_returned = ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available.
        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._od_since is None:
                self._od_since = elapsed
            self._last_returned = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Estimate expected remaining downtime, to decide whether to wait.
        expected_wait = max(self._ema_down * 0.5, self._ema_down - self._down_elapsed)
        if slack_remaining >= expected_wait + soft_buffer:
            self._last_returned = ClusterType.NONE
            return ClusterType.NONE

        if self._od_since is None:
            self._od_since = elapsed
        self._last_returned = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
