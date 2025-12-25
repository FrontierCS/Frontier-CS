from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_threshold_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work_seconds(self) -> float:
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = float(self.task_duration) - done
        if remaining < 0:
            return 0.0
        return remaining

    def _should_commit_to_od(self) -> bool:
        # Compute conservative latest time to switch to OD
        # Ensure we can react within one step's latency
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        remaining = self._remaining_work_seconds()
        if remaining <= 0:
            return False

        # If already on OD, no restart overhead to continue. Else, include restart overhead for switching.
        on_od_now = self.env.cluster_type == ClusterType.ON_DEMAND
        od_overhead = 0.0 if on_od_now else float(self.restart_overhead)

        # Slack after immediate switch to OD:
        # slack = time_left - (od_overhead + remaining)
        slack = time_left - (od_overhead + remaining)

        # Reaction margin: account for one-step decision latency with a small buffer.
        commit_margin = max(gap, 30.0)  # at least one gap or 30s

        return slack <= commit_margin

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, stay there until completion.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to on-demand now.
        if self._should_commit_to_od():
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available; pause if not, to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)