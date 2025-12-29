from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization based on spec_path (unused here).
        return self

    def _compute_work_done(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        first = segments[0]

        # Case 1: list of numeric durations
        if isinstance(first, (int, float)):
            for v in segments:
                try:
                    total += float(v)
                except (TypeError, ValueError):
                    continue
            return total

        # Case 2: list of (start, end) pairs
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            for seg in segments:
                try:
                    start = float(seg[0])
                    end = float(seg[1])
                    if end > start:
                        total += end - start
                except (TypeError, ValueError, IndexError):
                    continue
            return total

        # Fallback: try to coerce each element to float
        for v in segments:
            try:
                total += float(v)
            except (TypeError, ValueError):
                continue
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._compute_work_done()
        remaining = self.task_duration - work_done
        if remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            # Already at or past deadline; best-effort: finish as quickly as possible.
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Once committed to on-demand, always use it until the task is done.
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Conservative minimum time needed to finish via on-demand from now:
        # always include one restart overhead.
        fallback_need = remaining + self.restart_overhead

        # If fallback_need exceeds available time, or exactly fits, no slack remains:
        # must switch to on-demand now (though if fallback_need > time_left,
        # the deadline is already unsalvageable).
        if fallback_need >= time_left:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Slack we can safely spend on "no progress" time (waiting or unlucky spot).
        slack = time_left - fallback_need
        gap = self.env.gap_seconds

        # If we have at least one timestep of slack, we can afford to gamble on spot.
        if slack >= gap:
            if has_spot:
                return ClusterType.SPOT
            # No spot: wait and preserve money while we still have slack.
            return ClusterType.NONE

        # Slack is less than one timestep: any further delay risks missing deadline.
        self._commit_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)