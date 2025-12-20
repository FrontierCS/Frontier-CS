from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self._policy_initialized = False
        self.od_committed = False
        self.always_on_demand = False
        return self

    def _initialize_policy(self):
        # Initialize policy parameters based on environment/task specs.
        self.initial_slack = max(0.0, float(self.deadline - self.task_duration))
        restart_overhead = float(self.restart_overhead)

        # Thresholds based on initial slack and restart overhead.
        # Idle threshold: we allow idling (NONE) only while remaining slack above this.
        # Conservative buffer: once remaining slack drops below this, we commit to ON_DEMAND.
        if self.initial_slack <= 0.0:
            self.idle_slack_threshold = 0.0
            self.conservative_buffer = 0.0
        else:
            self.idle_slack_threshold = max(0.5 * self.initial_slack, 5.0 * restart_overhead)
            self.conservative_buffer = max(0.15 * self.initial_slack, 3.0 * restart_overhead)

        # If slack is extremely small relative to restart overhead, always use on-demand.
        self.always_on_demand = self.initial_slack <= 2.0 * restart_overhead

        self._policy_initialized = True

    def _get_task_done(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if segments is None:
            return 0.0
        try:
            if isinstance(segments, (list, tuple)):
                return float(sum(segments))
            return float(segments)
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._initialize_policy()
            self.od_committed = False

        # Compute completed work and remaining work.
        done = self._get_task_done()
        task_duration = float(self.task_duration)
        remaining_work = max(0.0, task_duration - done)

        # If task is effectively finished, do nothing.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we must always use on-demand due to negligible slack.
        if self.always_on_demand:
            return ClusterType.ON_DEMAND

        # Current time and remaining time to deadline.
        current_time = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        remaining_time = max(0.0, deadline - current_time)
        restart_overhead = float(self.restart_overhead)

        # Slack accounting.
        initial_slack = self.initial_slack
        used_slack = max(0.0, current_time - done)
        remaining_slack = initial_slack - used_slack

        # Final safety check: ensure enough time to finish on pure on-demand from now.
        # If not enough time, we must commit to ON_DEMAND immediately.
        if remaining_time <= remaining_work + restart_overhead:
            self.od_committed = True

        # If slack is exhausted or below conservative buffer, commit to ON_DEMAND.
        if remaining_slack <= 0.0 or remaining_slack <= self.conservative_buffer:
            self.od_committed = True

        if self.od_committed:
            return ClusterType.ON_DEMAND

        # Non-committed phase: decide based on spot availability and remaining slack.

        if has_spot:
            # When spot is available and we are not yet committed, prefer spot for cost savings.
            return ClusterType.SPOT

        # No spot available: decide between waiting (NONE) or using on-demand.
        # If we still have comfortable slack, we can afford to wait for spot.
        if remaining_slack > self.idle_slack_threshold:
            return ClusterType.NONE

        # Slack is getting tight: use on-demand to maintain progress.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
