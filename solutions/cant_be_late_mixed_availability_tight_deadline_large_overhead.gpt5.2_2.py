import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        def __init__(self, *args, **kwargs):
            pass


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

        self._last_elapsed: Optional[float] = None
        self._ema_p: float = 0.5
        self._alpha: float = 0.05
        self._spot_up_streak: int = 0

        self._committed_od: bool = False

        self._restart_steps: int = 1
        self._overhead_cluster: ClusterType = ClusterType.NONE
        self._overhead_steps_left: int = 0

        self._commit_extra: float = 0.0
        self._wait_extra: float = 0.0
        self._rounding_buffer: float = 0.0

        self._switch_min_work: float = 0.0
        self._switch_slack_needed: float = 0.0
        self._switch_min_p: float = 0.25
        self._spot_streak_needed: int = 2

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _reset_episode_state(self) -> None:
        self._last_elapsed = None
        self._ema_p = 0.5
        self._alpha = 0.05
        self._spot_up_streak = 0
        self._committed_od = False
        self._overhead_cluster = ClusterType.NONE
        self._overhead_steps_left = 0

        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._restart_steps = max(1, int(math.ceil(ro / gap))) if ro > 0 else 1

        self._rounding_buffer = gap
        self._commit_extra = max(2.0 * ro, 4.0 * gap)
        self._wait_extra = max(gap, 0.5 * ro)

        self._switch_min_work = max(2.0 * 3600.0, 8.0 * ro)
        self._switch_slack_needed = max(3600.0, 2.0 * ro + 2.0 * gap)
        self._spot_streak_needed = max(2, int(math.ceil(ro / gap)) + 1) if ro > 0 else 2

    def _maybe_reset(self) -> None:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if self._last_elapsed is None:
            self._reset_episode_state()
            self._last_elapsed = elapsed
            return
        if elapsed < self._last_elapsed - 1e-9 or elapsed <= 1e-9:
            self._reset_episode_state()
        self._last_elapsed = elapsed

    def _advance_overhead_counter(self, last_cluster_type: ClusterType) -> None:
        if self._overhead_steps_left <= 0:
            return
        if last_cluster_type == self._overhead_cluster and last_cluster_type != ClusterType.NONE:
            self._overhead_steps_left -= 1
            if self._overhead_steps_left <= 0:
                self._overhead_steps_left = 0
                self._overhead_cluster = ClusterType.NONE
        else:
            self._overhead_steps_left = 0
            self._overhead_cluster = ClusterType.NONE

    def _start_overhead(self, cluster: ClusterType) -> None:
        if cluster == ClusterType.NONE:
            self._overhead_steps_left = 0
            self._overhead_cluster = ClusterType.NONE
            return
        self._overhead_cluster = cluster
        self._overhead_steps_left = self._restart_steps

    def _compute_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        try:
            if isinstance(td, (int, float)):
                return float(td)

            if isinstance(td, dict):
                for k in ("done", "work_done", "seconds", "duration"):
                    if k in td:
                        return float(td[k])
                return 0.0

            if not isinstance(td, (list, tuple)) or len(td) == 0:
                return 0.0

            first = td[0]
            if isinstance(first, dict):
                total = 0.0
                for seg in td:
                    if not isinstance(seg, dict):
                        continue
                    if "duration" in seg:
                        total += float(seg["duration"])
                    elif "start" in seg and "end" in seg:
                        total += float(seg["end"]) - float(seg["start"])
                    elif "s" in seg and "e" in seg:
                        total += float(seg["e"]) - float(seg["s"])
                return max(0.0, total)

            if isinstance(first, (list, tuple)) and len(first) == 2:
                total = 0.0
                for a, b in td:
                    total += float(b) - float(a)
                return max(0.0, total)

            if isinstance(first, (int, float)):
                nums = [float(x) for x in td]
                s = float(sum(nums))
                mx = float(max(nums))
                dur = float(getattr(self, "task_duration", 0.0) or 0.0)
                if dur > 0:
                    if mx <= dur * 1.1 and mx >= s * 0.9:
                        return min(nums[-1], dur)
                    return min(s, dur)
                return max(0.0, s)
        except Exception:
            return 0.0

        return 0.0

    def _expected_wait_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        p = max(1e-3, min(0.999, float(self._ema_p)))
        exp_steps = (1.0 / p) - 1.0
        return max(0.0, exp_steps) * gap

    def _should_wait_for_spot(self, remaining_work: float, remaining_time: float) -> bool:
        if remaining_work <= 0.0:
            return False
        slack = remaining_time - remaining_work
        if slack <= 0.0:
            return False
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        exp_wait = self._expected_wait_seconds()
        return slack > (exp_wait + ro + self._wait_extra)

    def _should_switch_to_spot(self, remaining_work: float, remaining_time: float) -> bool:
        if remaining_work < self._switch_min_work:
            return False
        slack = remaining_time - remaining_work
        if slack < self._switch_slack_needed:
            return False
        if self._ema_p < self._switch_min_p:
            return False
        if self._spot_up_streak < self._spot_streak_needed:
            return False
        return True

    def _commit_check(self, last_cluster_type: ClusterType, remaining_work: float, remaining_time: float) -> bool:
        if remaining_work <= 0.0:
            return False
        required = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            required += float(getattr(self, "restart_overhead", 0.0) or 0.0)
        required += self._rounding_buffer
        return remaining_time <= (required + self._commit_extra)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset()

        self._ema_p = (1.0 - self._alpha) * self._ema_p + self._alpha * (1.0 if has_spot else 0.0)
        if has_spot:
            self._spot_up_streak += 1
        else:
            self._spot_up_streak = 0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed

        done = self._compute_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = task_duration - done

        if remaining_work <= 1e-6:
            return ClusterType.NONE

        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        self._advance_overhead_counter(last_cluster_type)

        if not self._committed_od and self._commit_check(last_cluster_type, remaining_work, remaining_time):
            self._committed_od = True
            self._overhead_steps_left = 0
            self._overhead_cluster = ClusterType.NONE
            return ClusterType.ON_DEMAND

        if self._committed_od:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._start_overhead(ClusterType.ON_DEMAND)
            return ClusterType.ON_DEMAND

        if self._overhead_steps_left > 0:
            if self._overhead_cluster == ClusterType.SPOT and not has_spot:
                self._overhead_steps_left = 0
                self._overhead_cluster = ClusterType.NONE
            else:
                return self._overhead_cluster

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._should_switch_to_spot(remaining_work, remaining_time):
                    self._start_overhead(ClusterType.SPOT)
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            if last_cluster_type != ClusterType.SPOT:
                self._start_overhead(ClusterType.SPOT)
            return ClusterType.SPOT

        # has_spot == False
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        if self._should_wait_for_spot(remaining_work, remaining_time):
            return ClusterType.NONE

        self._start_overhead(ClusterType.ON_DEMAND)
        return ClusterType.ON_DEMAND
