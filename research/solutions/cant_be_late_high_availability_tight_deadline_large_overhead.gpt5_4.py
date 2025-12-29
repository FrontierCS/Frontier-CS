from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "just_in_time_od"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False
        self._commit_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic environment values
        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        deadline = getattr(self, "deadline", elapsed + gap) or (elapsed + gap)
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        task_duration = getattr(self, "task_duration", 0.0) or 0.0

        # Progress done so far
        done_list = getattr(self, "task_done_time", None)
        if not done_list:
            done = 0.0
        else:
            try:
                done = float(sum(done_list))
            except Exception:
                # Fallback if env changes format unexpectedly
                done = 0.0

        remaining = max(0.0, task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        # If we have already committed to OD, keep using it
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Determine if we must commit to OD now to guarantee finish
        start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Safety margin accounts for discretization and decision latency under preemption.
        margin = max(gap * 2.0, restart_overhead * 0.5)

        must_commit = time_left <= (remaining + start_overhead + margin)
        if must_commit:
            self._committed_to_od = True
            self._commit_time = elapsed
            return ClusterType.ON_DEMAND

        # Not yet critical: prefer SPOT if available; otherwise wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)