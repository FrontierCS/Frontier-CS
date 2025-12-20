from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_safety_commit_v2"

    def __init__(self, args=None):
        super().__init__(args)
        # Configurable parameters (in minutes), with robust defaults
        self.buffer_minutes = getattr(args, "buffer_minutes", 45.0) if args is not None else 45.0
        self.wait_slack_minutes = getattr(args, "wait_slack_minutes", 60.0) if args is not None else 60.0

        # Internal state
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self):
        # Remaining compute work in seconds
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already finished, do nothing
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time metrics (seconds)
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        # Dynamic safety buffers (seconds)
        base_buffer_sec = max(int(self.buffer_minutes * 60), int(4 * self.restart_overhead), int(2 * self.env.gap_seconds))
        wait_slack_sec = max(int(self.wait_slack_minutes * 60), base_buffer_sec)

        # Decide commitment to On-Demand
        # Commit if the remaining slack is at/below the safety buffer
        slack = remaining_time - remaining_work
        if not self._committed_to_od and slack <= base_buffer_sec:
            self._committed_to_od = True

        # If already committed, stick with On-Demand to avoid risk
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed yet:
        if has_spot:
            # Use Spot when available before commitment threshold
            return ClusterType.SPOT

        # Spot not available:
        # If we still have enough slack, wait to save cost; otherwise commit to On-Demand
        if slack >= wait_slack_sec:
            return ClusterType.NONE
        else:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--buffer-minutes", type=float, default=45.0)
        parser.add_argument("--wait-slack-minutes", type=float, default=60.0)
        args, _ = parser.parse_known_args()
        return cls(args)
