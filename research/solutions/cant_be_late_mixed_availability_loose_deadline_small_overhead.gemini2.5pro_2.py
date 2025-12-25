import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self._work_done_cache: float = 0.0
        self._last_len_task_done_time: int = 0
        self._constant_safety_buffer: float = 120.0
        return self

    def _get_work_done(self) -> float:
        num_segments = len(self.task_done_time)
        if num_segments > self._last_len_task_done_time:
            new_segments = self.task_done_time[self._last_len_task_done_time:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._last_len_task_done_time = num_segments
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # The safety margin represents the time lost in a worst-case failure
        # (a preemption), which includes the wasted time step and the subsequent
        # restart overhead period.
        safety_margin = (self.restart_overhead +
                         self.env.gap_seconds +
                         self._constant_safety_buffer)

        # If the remaining work requires more time than we have left before the
        # deadline (minus our safety margin), we must use the reliable
        # On-Demand instance to guarantee progress.
        if work_remaining >= time_to_deadline - safety_margin:
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack. We can afford to use cheaper options.
            if has_spot:
                # Spot is available and is the cheapest way to make progress.
                return ClusterType.SPOT
            else:
                # Spot is unavailable. Waiting (NONE) is cheaper than On-Demand,
                # and our safety check ensures we have enough slack to wait.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)