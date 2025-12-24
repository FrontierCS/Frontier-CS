import math
from typing import Any

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:  # Fallbacks for local testing without the real package
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class DummyEnv:
        def __init__(self):
            self.elapsed_seconds = 0.0
            self.gap_seconds = 300.0
            self.cluster_type = ClusterType.NONE

    class Strategy:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.env = DummyEnv()
            self.task_duration = 48 * 3600.0
            self.task_done_time = []
            self.deadline = 52 * 3600.0
            self.restart_overhead = 0.05 * 3600.0

        def solve(self, spec_path: str):
            return self


class Solution(Strategy):
    NAME = "cant_be_late_hybrid_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        # Cached total completed task time (seconds)
        self._done_time_cache = 0.0
        self._done_time_len = 0

        # Once we commit to on-demand, never go back to spot/none
        self._committed_to_od = False

        # Slack thresholds (seconds)
        # When slack < _commit_slack: always use ON_DEMAND
        self._commit_slack = 1.0 * 3600.0  # 1 hour
        # When no spot and slack > _idle_slack: we can afford to wait (NONE)
        self._idle_slack = 2.0 * 3600.0    # 2 hours

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path to adjust thresholds.
        return self

    def _update_progress_cache(self) -> None:
        """Incrementally update cached completed task time."""
        task_done_time = getattr(self, "task_done_time", None)
        if task_done_time is None:
            return

        n = len(task_done_time)
        if n <= self._done_time_len:
            return

        for i in range(self._done_time_len, n):
            seg = task_done_time[i]
            dur = 0.0
            if isinstance(seg, (tuple, list)):
                if len(seg) >= 2:
                    try:
                        dur = float(seg[1]) - float(seg[0])
                    except Exception:
                        dur = 0.0
            else:
                try:
                    dur = float(seg)
                except Exception:
                    dur = 0.0

            if dur > 0.0:
                self._done_time_cache += dur

        self._done_time_len = n

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        if task_duration > 0.0 and self._done_time_cache > task_duration:
            self._done_time_cache = task_duration

    def _estimate_remaining_work(self) -> float:
        """Estimate remaining task duration (seconds)."""
        self._update_progress_cache()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._done_time_cache
        remaining = task_duration - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, always stay on-demand.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        remaining_work = self._estimate_remaining_work()

        # If task is done (or nearly done), don't spend more.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_remaining = deadline - elapsed
        if time_remaining < 0.0:
            time_remaining = 0.0

        # Slack = time remaining - work remaining
        slack = time_remaining - remaining_work

        # If we somehow have no slack left, must go all-in on on-demand.
        if slack <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Commit to on-demand when slack is small.
        if slack < self._commit_slack:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Ensure idle slack is at least commit slack.
        if self._idle_slack < self._commit_slack:
            self._idle_slack = self._commit_slack

        # If spot is available and we're not in the danger zone, use spot.
        if has_spot:
            return ClusterType.SPOT

        # No spot available: decide between waiting and using on-demand.
        if slack > self._idle_slack:
            # Plenty of slack: we can wait for cheaper spot.
            return ClusterType.NONE
        else:
            # Slack shrinking: use on-demand to maintain schedule.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
