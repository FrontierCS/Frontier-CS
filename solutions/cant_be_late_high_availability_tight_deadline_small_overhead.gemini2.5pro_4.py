import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_safety_margin"

    def solve(self, spec_path: str) -> "Solution":
        self.history_window_seconds = 3600
        self.min_safety_margin = 15 * 60
        self.max_safety_margin = 75 * 60
        self.spot_history = collections.deque()
        self.initial_availability_guess = 0.60
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds

        self.spot_history.append((current_time, 1 if has_spot else 0))
        while self.spot_history and self.spot_history[0][0] <= current_time - self.history_window_seconds:
            self.spot_history.popleft()

        if len(self.spot_history) < 20:
            recent_availability = self.initial_availability_guess
        else:
            available_count = sum(h[1] for h in self.spot_history)
            recent_availability = available_count / len(self.spot_history)

        margin_range = self.max_safety_margin - self.min_safety_margin
        safety_margin = self.max_safety_margin - recent_availability * margin_range

        time_left_until_deadline = self.deadline - current_time
        time_needed_on_demand = work_left + self.restart_overhead

        if time_left_until_deadline <= time_needed_on_demand + safety_margin:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        # The constructor needs to be able to be called with args.
        try:
            return cls(args)
        except TypeError:
            return cls()
