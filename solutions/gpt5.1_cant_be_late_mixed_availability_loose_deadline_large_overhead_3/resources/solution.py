from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.force_on_demand = False
        self._done_sum_cache = 0.0
        self._last_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached sum of completed work
        td = getattr(self, "task_done_time", None)
        if td is not None:
            current_len = len(td)
            if current_len != self._last_done_len:
                new_sum = 0.0
                for i in range(self._last_done_len, current_len):
                    new_sum += td[i]
                self._done_sum_cache += new_sum
                self._last_done_len = current_len
            done = self._done_sum_cache
        else:
            done = 0.0

        remaining = max(self.task_duration - done, 0.0)

        # If task is already done, avoid any cost.
        if remaining <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = max(self.deadline - elapsed, 0.0)
        dt = self.env.gap_seconds

        # Slack function: time left minus time needed on OD plus one restart overhead.
        F = time_left - (remaining + self.restart_overhead)

        # If we've already committed to on-demand, stick with it.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Commit to on-demand when slack becomes small enough.
        if F <= dt:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # In the flexible phase: prefer spot when available, otherwise pause.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
