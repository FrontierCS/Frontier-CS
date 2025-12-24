import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        self._initialized = False
        self._last_elapsed = -1.0

        self._done_est = 0.0

        self._spot_streak = 0
        self._cooldown_until = 0.0
        self._od_lock = False

        self._stable_spot_seconds = 15 * 60.0
        self._cooldown_seconds = 20 * 60.0
        self._stable_steps: Optional[int] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode(self):
        self._done_est = 0.0
        self._spot_streak = 0
        self._cooldown_until = 0.0
        self._od_lock = False
        self._stable_steps = None
        self._last_elapsed = -1.0

    def _get_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return float(getattr(self, "_done_est", 0.0))
        if isinstance(tdt, (int, float)):
            return float(tdt)
        if not isinstance(tdt, (list, tuple)) or len(tdt) == 0:
            return 0.0

        task_dur = float(getattr(self, "task_duration", 0.0))

        def _is_num(x):
            return isinstance(x, (int, float)) and math.isfinite(float(x))

        sum_candidate = 0.0
        last_candidate = None

        last_elem = tdt[-1]
        if _is_num(last_elem):
            last_candidate = float(last_elem)
        elif isinstance(last_elem, (list, tuple)) and last_elem:
            if _is_num(last_elem[-1]):
                last_candidate = float(last_elem[-1])

        for e in tdt:
            if _is_num(e):
                sum_candidate += float(e)
            elif isinstance(e, (list, tuple)) and len(e) >= 2 and _is_num(e[0]) and _is_num(e[1]):
                a = float(e[0])
                b = float(e[1])
                if b >= a:
                    sum_candidate += max(0.0, b - a)
                else:
                    sum_candidate += max(0.0, b)
            elif isinstance(e, (list, tuple)) and len(e) == 1 and _is_num(e[0]):
                sum_candidate += float(e[0])

        done = 0.0
        if 0.0 <= sum_candidate <= task_dur * 1.1:
            done = sum_candidate
        elif last_candidate is not None and 0.0 <= last_candidate <= task_dur * 1.1:
            done = last_candidate
        else:
            candidates = []
            if last_candidate is not None:
                candidates.append(last_candidate)
            candidates.append(sum_candidate)
            best = max(candidates) if candidates else 0.0
            done = max(0.0, min(task_dur, best))

        if done < self._done_est:
            done = self._done_est
        else:
            self._done_est = done
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)

        if self._last_elapsed < 0 or elapsed < self._last_elapsed or (elapsed == 0.0 and self._last_elapsed > 0.0):
            self._reset_episode()
        self._last_elapsed = elapsed

        if has_spot:
            self._spot_streak += 1
        else:
            self._spot_streak = 0

        if self._stable_steps is None:
            g = max(1.0, gap)
            self._stable_steps = max(1, int(math.ceil(self._stable_spot_seconds / g)))

        done = self._get_done_seconds()
        remaining_work = float(self.task_duration) - done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = float(self.deadline) - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND if not has_spot else ClusterType.SPOT

        h = float(self.restart_overhead)
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else h

        slack = time_left - remaining_work

        buffer_reserve = max(2.0 * gap, 15.0 * 60.0)
        reserve = 2.0 * h + buffer_reserve

        buffer_critical = max(2.0 * gap, 5.0 * 60.0)
        critical = h + buffer_critical

        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._cooldown_until = max(self._cooldown_until, elapsed + self._cooldown_seconds)

        if not self._od_lock:
            if slack <= critical and slack >= overhead_to_od:
                self._od_lock = True
            elif time_left <= remaining_work + overhead_to_od + buffer_critical:
                self._od_lock = True

        if self._od_lock:
            if slack < overhead_to_od and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if not has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if slack > reserve + gap:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            if elapsed < self._cooldown_until:
                return ClusterType.ON_DEMAND
            if self._spot_streak >= (self._stable_steps or 1) and slack > reserve:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
