import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Strategy parameters
        # If slack is less than this many restart_overheads, use On-Demand exclusively.
        self.danger_zone_factor = 2.0
        # If slack is less than this many restart_overheads, use On-Demand
        # instead of waiting when Spot is unavailable.
        self.caution_zone_factor = 5.0

        self.danger_zone_slack_threshold = self.danger_zone_factor * self.restart_overhead
        self.caution_zone_slack_threshold = self.caution_zone_factor * self.restart_overhead
        
        # Cache for memoizing completed work calculation
        self._work_done_cache = 0.0
        self._task_done_time_len_cache = 0

        return self

    def _get_work_done(self) -> float:
        """Calculates total work done, caching the result for efficiency."""
        current_len = len(self.task_done_time)
        if current_len > self._task_done_time_len_cache:
            new_segments = self.task_done_time[self._task_done_time_len_cache:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._task_done_time_len_cache = current_len
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_needed_for_guaranteed_finish = work_remaining + self.env.remaining_restart_overhead
        
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - time_needed_for_guaranteed_finish

        if current_slack <= self.danger_zone_slack_threshold:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        
        if current_slack <= self.caution_zone_slack_threshold:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)