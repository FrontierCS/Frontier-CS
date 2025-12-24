from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import argparse

class Solution(Strategy):
    NAME = "conservative_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        progress = sum(self.task_done_time)
        remaining = self.task_duration - progress
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if remaining <= 0 or time_left <= 0:
            return ClusterType.NONE
        if not has_spot:
            return ClusterType.ON_DEMAND
        ratio = remaining / time_left if time_left > 0 else float('inf')
        threshold = 0.9
        if ratio >= threshold:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
