import math
from collections import deque

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self._reset_state()

    def _reset_state(self):
        self._spot_down_streak = 0
        self._spot_up_streak = 0
        self._down_streak_history = deque(maxlen=200)
        self._in_final_od = False
        self._last_decision = ClusterType.NONE

    def solve(self, spec_path: str) -> "Solution":
        self._reset_state()
        self.spec_path = spec_path
        return self

    @staticmethod
    def _as_seconds(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    def _done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        if isinstance(tdt, (int, float)):
            return float(tdt)

        if isinstance(tdt, (list, tuple)):
            if not tdt:
                return 0.0

            # If list of (start,end) segments
            if isinstance(tdt[0], (list, tuple)) and len(tdt[0]) == 2:
                total = 0.0
                for seg in tdt:
                    try:
                        a, b = seg
                        total += max(0.0, float(b) - float(a))
                    except Exception:
                        continue
                return total

            # If list of numbers (either per-segment durations or cumulative done)
            nums = []
            for v in tdt:
                if isinstance(v, (int, float)):
                    nums.append(float(v))
            if not nums:
                return 0.0

            s = sum(nums)
            m = max(nums)
            td = self._as_seconds(getattr(self, "task_duration", 0.0))
            if td > 0:
                # Heuristic: if sum exceeds task duration significantly but max does not,
                # interpret as cumulative values.
                if m <= td * 1.05 and s > td * 1.10:
                    return m
                if s <= td * 1.20:
                    return s
                return min(max(s, m), td)
            return max(s, m)

        return 0.0

    @staticmethod
    def _p90(values, default_val):
        if not values:
            return default_val
        arr = sorted(values)
        n = len(arr)
        if n == 1:
            return arr[0]
        idx = int(math.ceil(0.90 * (n - 1)))
        return arr[min(max(idx, 0), n - 1)]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot availability streak stats
        gap = self._as_seconds(getattr(self.env, "gap_seconds", 0.0))
        if gap <= 0:
            gap = 60.0

        if has_spot:
            self._spot_up_streak += 1
            if self._spot_down_streak > 0:
                self._down_streak_history.append(self._spot_down_streak * gap)
                self._spot_down_streak = 0
        else:
            self._spot_down_streak += 1
            self._spot_up_streak = 0

        elapsed = self._as_seconds(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = self._as_seconds(getattr(self, "deadline", 0.0))
        task_duration = self._as_seconds(getattr(self, "task_duration", 0.0))
        overhead = self._as_seconds(getattr(self, "restart_overhead", 0.0))

        done = self._done_work_seconds()
        if task_duration > 0:
            done = min(done, task_duration)
        remaining_work = max(0.0, task_duration - done)

        if remaining_work <= 0:
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)
        slack = remaining_time - remaining_work

        # Safety margins
        base_buffer = max(2.0 * 3600.0, 8.0 * overhead + 4.0 * gap)  # ~2h or more
        final_lock_slack = base_buffer

        # Once slack becomes tight, commit to on-demand to minimize deadline risk.
        if slack <= final_lock_slack:
            self._in_final_od = True

        if self._in_final_od:
            self._last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Not in final lock mode
        if has_spot:
            # If currently on OD, only switch back to spot when spot looks stable and slack is ample
            if self._last_decision == ClusterType.ON_DEMAND:
                stable_steps = 3
                if self._spot_up_streak >= stable_steps and slack >= (final_lock_slack + 4.0 * overhead + 2.0 * gap):
                    self._last_decision = ClusterType.SPOT
                    return ClusterType.SPOT
                self._last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND

            self._last_decision = ClusterType.SPOT
            return ClusterType.SPOT

        # No spot available: choose between waiting (NONE) and on-demand
        wait_budget = slack - (final_lock_slack + overhead + gap)

        # Cap waiting during an outage to avoid consuming all slack on long outages.
        default_p90 = 3.0 * 3600.0
        p90_down = self._p90(self._down_streak_history, default_p90)

        dyn_cap = 0.25 * max(0.0, slack)
        dyn_cap = max(3600.0, min(dyn_cap, 6.0 * 3600.0))  # [1h, 6h]
        cap = min(dyn_cap, max(3600.0, p90_down))

        down_time = self._spot_down_streak * gap

        # If we have enough wait budget and this outage hasn't exceeded our cap,
        # wait for spot (free) instead of using on-demand.
        if wait_budget > 0 and down_time < cap and self._last_decision != ClusterType.ON_DEMAND:
            self._last_decision = ClusterType.NONE
            return ClusterType.NONE

        self._last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)