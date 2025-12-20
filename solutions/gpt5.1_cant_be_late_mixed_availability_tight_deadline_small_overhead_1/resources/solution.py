import json
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, *args, **kwargs):
        # Call parent constructor robustly, regardless of its exact signature.
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass

        # Strategy parameters (in seconds).
        # Above safe_slack_seconds: we are comfortable waiting when no spot.
        # At or below critical_slack_seconds: permanently switch to on-demand.
        self.safe_slack_seconds = 3.0 * 3600.0
        self.critical_slack_seconds = 1.0 * 3600.0

        # Internal state.
        self.lock_on_demand = False
        self.total_steps = 0
        self.spot_available_steps = 0
        self.spec = None

    def solve(self, spec_path: str) -> "Solution":
        if spec_path:
            try:
                with open(spec_path, "r") as f:
                    self.spec = json.load(f)
            except Exception:
                self.spec = None
        return self

    def _compute_slack(self) -> float:
        """Compute remaining slack time (seconds)."""
        try:
            done = sum(self.task_done_time) if self.task_done_time is not None else 0.0
        except TypeError:
            # In case task_done_time is a scalar or otherwise non-iterable.
            done = float(self.task_done_time) if self.task_done_time else 0.0

        remaining_work = max(self.task_duration - done, 0.0)
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)
        slack = time_left - remaining_work
        return slack

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1

        slack = self._compute_slack()

        # Once slack falls below the critical threshold, lock into on-demand.
        if not self.lock_on_demand and slack <= self.critical_slack_seconds:
            self.lock_on_demand = True

        if self.lock_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            # Prefer spot whenever available while we still have sufficient slack.
            return ClusterType.SPOT

        # Spot not available and not yet locked into on-demand.
        # If we still have plenty of slack, we can wait; otherwise, use on-demand.
        if slack > self.safe_slack_seconds:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
