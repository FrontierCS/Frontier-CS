from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_threshold"

    def solve(self, spec_path: str) -> "Solution":
        # No external configuration used; ensure any state is reset per evaluation.
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        t = float(env.elapsed_seconds)
        gap = float(env.gap_seconds)
        deadline = float(self.deadline)
        restart_overhead = float(self.restart_overhead)

        # Compute remaining useful work (in seconds)
        done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        remaining_work = float(self.task_duration) - done

        # If task is done (or numerically very close), stop using resources
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Safety margin accounts for:
        # - One or two possible restart overheads near the end
        # - A few step-size rounding errors
        safety_margin = restart_overhead * 2.0 + 3.0 * gap

        # Effective time required to safely finish if we switch to on-demand only
        effective_remaining = remaining_work + safety_margin

        # Latest time we can afford to *start* an all-on-demand schedule
        latest_start_allowed = deadline - effective_remaining

        # If choosing anything other than ON_DEMAND for the *next* gap could
        # cause us to miss this latest_start_allowed in the worst case
        # (i.e., we make zero progress in the coming gap), then we must
        # switch to ON_DEMAND now.
        if t + gap > latest_start_allowed:
            return ClusterType.ON_DEMAND

        # Before the safety threshold, use Spot whenever available; otherwise idle.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
