from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_dynamic_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization; we lazily initialize in _step.
        self._buffer_seconds = None
        self._work_done_cache = 0.0
        self._last_task_done_len = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization of buffer based on problem slack.
        if not hasattr(self, "_buffer_seconds") or self._buffer_seconds is None:
            # Total slack = deadline - task_duration - one restart_overhead.
            slack = self.deadline - self.task_duration - self.restart_overhead
            if slack <= 0:
                self._buffer_seconds = 0.0
            else:
                # Use 25% of available slack as a safety buffer.
                self._buffer_seconds = 0.25 * slack

        # Lazy initialization of work-done cache.
        if not hasattr(self, "_work_done_cache"):
            self._work_done_cache = 0.0
            self._last_task_done_len = 0

        # Incrementally maintain total work done.
        segments = self.task_done_time or []
        n = len(segments)
        if n > self._last_task_done_len:
            total = self._work_done_cache
            for i in range(self._last_task_done_len, n):
                total += segments[i]
            self._work_done_cache = total
            self._last_task_done_len = n

        work_done = self._work_done_cache
        remaining = self.task_duration - work_done
        if remaining <= 0:
            # Task already completed.
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        dt = self.env.gap_seconds
        time_left = self.deadline - now

        if time_left <= 0:
            # Already past deadline; just use on-demand.
            return ClusterType.ON_DEMAND

        # Slack after accounting for remaining work and a possible restart overhead.
        S = time_left - (remaining + self.restart_overhead)
        buffer = self._buffer_seconds

        # It is safe to "risk" (use spot or idle) this step if,
        # even in the worst case of zero progress this step,
        # we can still finish on time using only on-demand.
        safe_to_risk = S > buffer + dt + 1e-9

        if safe_to_risk:
            if has_spot:
                return ClusterType.SPOT
            else:
                # Wait for cheaper spot while we still have enough slack.
                return ClusterType.NONE
        else:
            # Not enough slack to risk; switch to guaranteed on-demand.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)