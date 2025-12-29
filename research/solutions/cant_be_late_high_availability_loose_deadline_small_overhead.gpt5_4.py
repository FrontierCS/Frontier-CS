from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v3"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._cached_done_sum = 0.0
        self._last_task_done_len = 0
        # Configurable safety buffers (in seconds) - can be overridden in solve() from spec if desired
        self.min_critical_buffer_seconds = 3600  # default: 1 hour safety near deadline
        self.extra_idle_guard_seconds = 0  # additional buffer for idling decisions

    def solve(self, spec_path: str) -> "Solution":
        # Optionally read config from spec_path; keep defaults if unavailable
        try:
            if spec_path:
                import json
                with open(spec_path, "r") as f:
                    cfg = json.load(f)
                self.min_critical_buffer_seconds = float(
                    cfg.get("min_critical_buffer_seconds", self.min_critical_buffer_seconds)
                )
                self.extra_idle_guard_seconds = float(
                    cfg.get("extra_idle_guard_seconds", self.extra_idle_guard_seconds)
                )
        except Exception:
            pass
        return self

    def _progress_done_seconds(self) -> float:
        lst = self.task_done_time
        if not isinstance(lst, (list, tuple)):
            # Fallback: try to read a scalar if provided
            try:
                return float(lst)  # type: ignore
            except Exception:
                return self._cached_done_sum
        n = len(lst)
        if n > self._last_task_done_len:
            # Incrementally add only new pieces
            try:
                delta_sum = sum(lst[self._last_task_done_len:n])
            except Exception:
                # Fallback to recompute full sum if slicing fails
                delta_sum = sum(lst) - self._cached_done_sum
            self._cached_done_sum += delta_sum
            self._last_task_done_len = n
        elif n < self._last_task_done_len:
            # In case list resets, recompute
            try:
                self._cached_done_sum = sum(lst)
                self._last_task_done_len = n
            except Exception:
                pass
        return self._cached_done_sum

    def _safe_buffers(self):
        # Dynamic critical buffer accounts for restart and step granularity
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        dynamic_component = 2.0 * overhead + 4.0 * gap
        critical = max(self.min_critical_buffer_seconds, dynamic_component)
        idle_guard = critical + self.extra_idle_guard_seconds
        return critical, idle_guard

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        done = self._progress_done_seconds()
        remaining_work = max(duration - done, 0.0)
        time_remaining = max(deadline - now, 0.0)

        # If already done, no need to run anything
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Slack budget: how much non-progress time we can still afford
        slack = time_remaining - remaining_work

        # Buffers
        critical_buffer, idle_guard = self._safe_buffers()

        # If slack is negative, we're behind; choose OD to salvage as much as possible
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Enter critical mode: always OD to avoid any further interruptions
        if slack <= critical_buffer:
            return ClusterType.ON_DEMAND

        # Outside of critical mode:
        if has_spot:
            # Use Spot while it's available to minimize cost
            return ClusterType.SPOT

        # No spot available:
        # Idle only if we can afford to lose one step without entering critical territory
        if slack - gap > idle_guard:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)