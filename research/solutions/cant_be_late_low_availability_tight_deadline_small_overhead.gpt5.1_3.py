import argparse
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class DummyEnv:
        def __init__(self):
            self.elapsed_seconds = 0.0
            self.gap_seconds = 60.0
            self.cluster_type = ClusterType.NONE

    class Strategy:
        NAME = "base_strategy"

        def __init__(self, args: Any = None):
            self.args = args
            self.env = DummyEnv()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0

        def solve(self, spec_path: str):
            return self


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._done_time_sum = 0.0
        self._last_segments_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_progress_cache(self) -> None:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return
        current_len = len(segments)
        if current_len > self._last_segments_len:
            # Incrementally update the total done time
            new_sum = 0.0
            for i in range(self._last_segments_len, current_len):
                new_sum += segments[i]
            self._done_time_sum += new_sum
            self._last_segments_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached completed work
        self._update_progress_cache()

        task_duration = getattr(self, "task_duration", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0

        env = self.env
        elapsed = getattr(env, "elapsed_seconds", 0.0) or 0.0
        gap = getattr(env, "gap_seconds", 1.0) or 1.0

        remaining_work = task_duration - self._done_time_sum
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0:
            # Already out of time; do the best we can
            return ClusterType.ON_DEMAND

        # Future overhead we conservatively account for when committing to on-demand
        future_overhead = restart_overhead

        # Slack (buffer) time we can afford to "waste" without making progress
        slack = time_left - remaining_work - future_overhead

        # If slack is large enough to risk another potentially unproductive step:
        # allow SPOT (if available) or NONE (if not) to save cost.
        if slack > gap:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # Slack is small: must rely on on-demand to safely finish before deadline.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)