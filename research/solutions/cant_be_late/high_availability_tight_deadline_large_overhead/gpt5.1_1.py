from typing import Any, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize internal state
        self.force_on_demand: bool = False
        self._cached_done: float = 0.0
        self._cached_len: int = 0
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy-init in case solve() was not called for some reason.
        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False
        if not hasattr(self, "_cached_done"):
            self._cached_done = 0.0
            self._cached_len = 0

        # Basic environment values
        env = self.env
        dt = float(getattr(env, "gap_seconds", 1.0))
        now = float(getattr(env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", now))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # If already past deadline or no work, just stop.
        if now >= deadline or task_duration <= 0:
            return ClusterType.NONE

        # Incremental computation of done work from task_done_time
        done = self._update_done_work()

        remaining = max(task_duration - done, 0.0)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = max(deadline - now, 0.0)
        if time_left <= 0.0:
            # Should not normally happen; return NONE to avoid illegal actions.
            return ClusterType.NONE

        # If we've previously committed to on-demand, always stay on it.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Safety buffer accounts for one future restart overhead plus discretization margin.
        overhead_buf = max(restart_overhead, 0.0) + 2.0 * dt
        minimal_slack_for_spot = 2.0 * dt

        # Slack under worst-case assumption: future spot/idle time yields zero progress.
        slack = time_left - remaining - overhead_buf

        # If slack too small, immediately commit to on-demand for the rest of the run.
        if slack <= minimal_slack_for_spot:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are still in the "exploration" window: use spot when available, otherwise idle.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    def _update_done_work(self) -> float:
        """Incrementally sum completed work from self.task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not isinstance(segments, list):
            # Fallback: cannot interpret segments; assume no progress.
            return float(getattr(self, "_cached_done", 0.0))

        curr_len = len(segments)
        # If list shrank (should not normally happen), recompute from scratch.
        if curr_len < self._cached_len:
            self._cached_done = 0.0
            self._cached_len = 0

        if curr_len > self._cached_len:
            inc = 0.0
            for i in range(self._cached_len, curr_len):
                seg = segments[i]
                inc += self._segment_duration(seg)
            self._cached_done += inc
            self._cached_len = curr_len

        return self._cached_done

    @staticmethod
    def _segment_duration(seg: Any) -> float:
        """Best-effort extraction of duration from a 'segment' object."""
        # Tuple or list [start, end]
        if isinstance(seg, (tuple, list)) and len(seg) >= 2:
            try:
                start, end = seg[0], seg[1]
                return max(float(end) - float(start), 0.0)
            except Exception:
                pass

        # Object with .start and .end attributes
        if hasattr(seg, "start") and hasattr(seg, "end"):
            try:
                start = getattr(seg, "start")
                end = getattr(seg, "end")
                return max(float(end) - float(start), 0.0)
            except Exception:
                pass

        # Fallback: treat as a scalar duration
        try:
            val = float(seg)
            return max(val, 0.0)
        except Exception:
            return 0.0