from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_guard_wait_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_state(self):
        self._committed_on_demand = False

    def _remaining_work(self) -> float:
        done = 0.0
        if hasattr(self, "task_done_time") and self.task_done_time:
            try:
                done = float(sum(self.task_done_time))
            except Exception:
                done = 0.0
        remaining = max(0.0, float(self.task_duration) - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize/reset episode state at the beginning of each episode
        if not hasattr(self, "_committed_on_demand"):
            self._reset_episode_state()
        # Detect new episode by elapsed time near zero
        if getattr(self.env, "elapsed_seconds", 0.0) <= 1e-9:
            self._reset_episode_state()

        # If already committed to OD, always continue OD
        if self._committed_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # If task already done, do nothing
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Core decision logic
        t = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        L = max(0.0, deadline - t)  # time left
        O = float(self.restart_overhead)

        # Safety margins
        gap = max(1.0, float(self.env.gap_seconds))  # ensure >= 1s
        switch_margin = max(gap, 300.0)  # at least one step or 5 minutes

        # If we switch to OD now (from not-OD), time needed = overhead + remaining
        needed_if_switch_now = O + remaining
        M = L - needed_if_switch_now  # slack if we switch to OD now

        # If we are too close to the deadline, switch to OD immediately
        if M <= switch_margin:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available; this maintains slack (R and L decrease together)
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait or switch to OD
        # Wait only if we retain at least one more step of cushion beyond switch margin
        if M >= switch_margin + gap:
            return ClusterType.NONE

        # Otherwise, commit to OD to ensure completion
        self._committed_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)