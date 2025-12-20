from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._force_on_demand = False
        # Minimum safety margin in seconds, in addition to at least one time step.
        self._min_margin_seconds = 60.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could load config from spec_path.
        return self

    def _estimate_done_time(self) -> float:
        """Conservative estimate of completed work time (in seconds).

        Uses the maximum of task_done_time list so we never overestimate progress,
        regardless of whether the list stores segment durations or cumulative times.
        """
        task_done = getattr(self, "task_done_time", None)
        if not task_done:
            return 0.0
        try:
            # task_done is iterable; take max to avoid overestimating progress
            done = max(task_done)
            return float(done)
        except Exception:
            # Fallback in case task_done is malformed
            try:
                return float(task_done)
            except Exception:
                return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, keep using it to avoid
        # further restart overheads and ensure completion.
        if self._force_on_demand:
            # If task already finished, stop to avoid unnecessary cost.
            done = self._estimate_done_time()
            total_dur = getattr(self, "task_duration", None)
            if total_dur is not None and done >= float(total_dur):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # If task duration is unknown for some reason, fall back to a simple baseline.
        total_dur = getattr(self, "task_duration", None)
        if total_dur is None:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        total_dur = float(total_dur)
        done = self._estimate_done_time()
        remaining_work = max(0.0, total_dur - done)

        # If work is already done, don't run more.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Get deadline and time left.
        deadline = getattr(self, "deadline", None)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        if deadline is None:
            # No deadline info: conservative baseline.
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        deadline = float(deadline)
        time_left = deadline - elapsed

        # If we're at or past the deadline, it's already too late; still choose OD.
        if time_left <= 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Safety margin based on time step size and a minimum absolute value.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0.0:
            gap = 1.0  # fallback if gap is missing or zero
        margin = max(gap, self._min_margin_seconds)

        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Slack if we immediately switch to on-demand and stick with it.
        # S_est = time_left - (remaining_work + restart_overhead)
        slack_if_commit = time_left - (remaining_work + restart_overhead)

        # If our slack has shrunk to within the safety margin, immediately
        # commit to on-demand to ensure we finish before the deadline
        # even in the worst case of future spot unavailability.
        if slack_if_commit <= margin:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # No Spot right now and still plenty of slack: wait to save cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
