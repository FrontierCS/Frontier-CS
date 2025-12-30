from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args):
        super().__init__(args)
        # Internal state for caching and control
        self._cached_done_total = 0.0
        self._cached_done_len = 0
        self._committed_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional: read spec_path if needed. Not used here.
        return self

    @classmethod
    def _from_args(cls, parser):  # REQUIRED
        args, _ = parser.parse_known_args()
        return cls(args)

    def _compute_total_done(self) -> float:
        """Compute total work done so far from task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            self._cached_done_total = 0.0
            self._cached_done_len = 0
            return 0.0

        n = len(segments)
        # Reset cache if length shrank or cache uninitialized
        if self._cached_done_len > n:
            self._cached_done_total = 0.0
            self._cached_done_len = 0

        total = self._cached_done_total
        for i in range(self._cached_done_len, n):
            seg = segments[i]
            val = 0.0
            if isinstance(seg, (int, float)):
                val = float(seg)
            elif isinstance(seg, (tuple, list)):
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    val = float(seg[1] - seg[0])
                else:
                    try:
                        val = float(seg)
                    except (TypeError, ValueError):
                        val = 0.0
            else:
                try:
                    val = float(seg)
                except (TypeError, ValueError):
                    val = 0.0
            total += val

        self._cached_done_total = total
        self._cached_done_len = n
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work and slack
        work_done = self._compute_total_done()
        total_duration = float(self.task_duration)
        remaining = max(0.0, total_duration - work_done)

        if remaining <= 0.0:
            # Task finished: no need to spend more
            return ClusterType.NONE

        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = max(0.0, deadline - now)

        slack = time_left - remaining  # in seconds

        # Compute dynamic thresholds
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Guard time before deadline to fully switch to on-demand.
        # Large enough to cover restart/step granularity under worst case.
        base_guard = 4.0 * 3600.0  # 4 hours
        dynamic_guard = 5.0 * (gap + overhead)
        guard = max(base_guard, dynamic_guard)

        # Extra slack above guard during which we allow idling when no spot
        idle_extra = 2.0 * max(3600.0, gap)
        idle_threshold = guard + idle_extra

        # Once committed to on-demand, never go back to spot
        if not self._committed_on_demand:
            if slack <= guard:
                self._committed_on_demand = True

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet committed: use spot when available
        if has_spot:
            return ClusterType.SPOT

        # No spot: decide whether to idle or use on-demand based on slack
        if slack > idle_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND