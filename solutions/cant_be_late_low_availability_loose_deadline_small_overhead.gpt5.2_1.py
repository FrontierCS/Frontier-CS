import math
from typing import Optional, Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_robust_v2"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._reset_state()

    def _reset_state(self) -> None:
        self._step_n = 0
        self._spot_avail_n = 0
        self._prev_has_spot = None

        self._consec_spot = 0
        self._consec_no_spot = 0

        self._spot_streak_len = 0
        self._spot_streak_count = 0
        self._spot_streak_total_steps = 0

        self._od_hold_until = 0.0
        self._final_phase = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _estimate_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        if not tdt:
            return 0.0

        def clamp(v: float) -> float:
            if v < 0.0:
                return 0.0
            if task_duration > 0.0 and v > task_duration:
                return task_duration
            return v

        try:
            if isinstance(tdt, (int, float)):
                return clamp(float(tdt))

            if isinstance(tdt, (list, tuple)):
                if not tdt:
                    return 0.0

                # If nested structures appear, attempt a reasonable sum of numeric entries.
                if isinstance(tdt[-1], (list, tuple)):
                    total = 0.0
                    last_cum = None
                    maybe_cumulative = True
                    for item in tdt:
                        if isinstance(item, (int, float)):
                            v = float(item)
                            total += v
                            if last_cum is not None and v < last_cum:
                                maybe_cumulative = False
                            last_cum = v
                        elif isinstance(item, (list, tuple)):
                            nums = [float(y) for y in item if isinstance(y, (int, float))]
                            if len(nums) == 2:
                                a, b = nums
                                if b >= a:
                                    total += (b - a)
                                else:
                                    total += a
                            else:
                                total += sum(nums)
                            maybe_cumulative = False
                        else:
                            maybe_cumulative = False
                    return clamp(total)

                nums = [float(x) for x in tdt if isinstance(x, (int, float))]
                if not nums:
                    return 0.0
                s = sum(nums)
                m = max(nums)

                monotonic = len(nums) >= 3 and all(nums[i] >= nums[i - 1] for i in range(1, len(nums)))
                if monotonic and (task_duration <= 0.0 or m <= task_duration) and s > m * 1.5:
                    return clamp(m)

                # Prefer sum if it doesn't exceed duration too much; otherwise fall back to max.
                if task_duration > 0.0 and s <= task_duration * 1.1:
                    return clamp(s)
                if task_duration > 0.0 and m <= task_duration:
                    return clamp(m)
                return clamp(s)

            return 0.0
        except Exception:
            return 0.0

    def _pessimistic_spot_prob(self) -> float:
        n = self._step_n
        if n <= 0:
            return 0.05
        alpha = 2.0
        p_hat = (self._spot_avail_n + alpha) / (n + 2.0 * alpha)
        p_hat = min(1.0, max(0.0, p_hat))
        stderr = math.sqrt(max(0.0, p_hat * (1.0 - p_hat)) / (n + 5.0))
        p_pess = p_hat - 2.0 * stderr - 0.03
        return min(1.0, max(0.01, p_pess))

    def _avg_spot_streak_seconds(self, gap: float) -> float:
        if self._spot_streak_count <= 0:
            return float("inf")
        return (self._spot_streak_total_steps / max(1, self._spot_streak_count)) * gap

    def _update_availability_stats(self, has_spot: bool) -> None:
        self._step_n += 1
        if has_spot:
            self._spot_avail_n += 1

        if has_spot:
            self._consec_spot = self._consec_spot + 1
            self._consec_no_spot = 0
        else:
            self._consec_no_spot = self._consec_no_spot + 1
            self._consec_spot = 0

        # Spot streak tracking (based on availability, not our usage).
        if has_spot:
            self._spot_streak_len += 1
        else:
            if self._spot_streak_len > 0:
                self._spot_streak_total_steps += self._spot_streak_len
                self._spot_streak_count += 1
                self._spot_streak_len = 0

        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_availability_stats(bool(has_spot))

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(self.env, "gap_seconds", 60.0), 60.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        work_done = self._estimate_work_done()
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)

        remaining_work = max(0.0, task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        # Reserves / hysteresis
        # Keep a decent buffer to absorb restart overheads and step granularity.
        final_reserve = max(2.0 * 3600.0, 12.0 * restart_overhead, 10.0 * gap)
        wait_reserve = final_reserve + max(2.0 * gap, 2.0 * restart_overhead)
        od_hold = max(10.0 * 60.0, 2.0 * restart_overhead, 3.0 * gap)

        # Enter final phase when slack is low; in final phase, avoid starting spot anew.
        if slack <= final_reserve:
            self._final_phase = True

        # If already in OD hold, keep OD to avoid churn (unless we are already on spot and can continue).
        in_hold = elapsed < self._od_hold_until

        if slack < 0.0:
            self._final_phase = True
            self._od_hold_until = max(self._od_hold_until, elapsed + od_hold)
            return ClusterType.ON_DEMAND

        if self._final_phase:
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            self._od_hold_until = max(self._od_hold_until, elapsed + od_hold)
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND and in_hold:
                return ClusterType.ON_DEMAND

            # Avoid switching from OD to spot for tiny/flake spot bursts.
            avg_streak_s = self._avg_spot_streak_seconds(gap)
            min_streak_needed = max(2.5 * restart_overhead, 2.0 * gap)
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._consec_spot < 2 and slack <= 3.0 * final_reserve:
                    return ClusterType.ON_DEMAND
                if avg_streak_s < min_streak_needed and slack <= 4.0 * final_reserve:
                    return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available
        if last_cluster_type == ClusterType.ON_DEMAND and in_hold:
            return ClusterType.ON_DEMAND

        if slack > wait_reserve:
            return ClusterType.NONE

        self._od_hold_until = max(self._od_hold_until, elapsed + od_hold)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
