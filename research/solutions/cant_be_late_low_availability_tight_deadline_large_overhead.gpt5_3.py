from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False
        self._prev_elapsed = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_if_new_run(self):
        # Detect new run by elapsed time reset
        if self._prev_elapsed < 0 or self.env.elapsed_seconds < self._prev_elapsed:
            self._committed_to_od = False
        self._prev_elapsed = self.env.elapsed_seconds

    def _commit_buffer(self, gap_seconds: float) -> float:
        # Small buffer to account for discretization/float errors
        base = 1.0  # seconds
        return max(base, 0.25 * gap_seconds)

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(self.task_duration - done, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_if_new_run()

        # If we're already running on on-demand, stick with it to avoid extra overhead risk.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_od = True

        remaining_work = self._remaining_work()
        if remaining_work <= 0:
            # Job is done
            self._committed_to_od = False
            return ClusterType.NONE

        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)
        gap = getattr(self.env, "gap_seconds", 1.0)
        buffer = self._commit_buffer(gap)

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to on-demand now
        # Overhead to start OD now (zero if currently on OD, otherwise restart_overhead)
        overhead_to_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        required_time_on_od = remaining_work + overhead_to_start_od

        if has_spot:
            # Use spot whenever available until we must commit to OD.
            # Running on spot this step does not worsen the (time_left - required_time_on_od) margin
            # because both time_left and remaining_work decrease by 'gap'.
            return ClusterType.SPOT

        # Spot not available: choose NONE if we can afford to wait one more step
        # Ensure that after idling for one gap, we can still finish on OD with buffer.
        if time_left - gap > required_time_on_od + buffer:
            return ClusterType.NONE

        # Otherwise, commit to on-demand now to guarantee finish by deadline.
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)