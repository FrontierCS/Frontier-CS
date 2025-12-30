from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safety_margin"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize per-episode state
        self.force_on_demand = False
        self.commit_threshold = None
        self._last_elapsed = None
        return self

    def _compute_work_done(self) -> float:
        """Robustly compute total work done from task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        first = segments[0]
        if isinstance(first, (int, float)):
            for x in segments:
                total += float(x)
        elif isinstance(first, (list, tuple)) and len(first) >= 2:
            for seg in segments:
                try:
                    total += float(seg[1]) - float(seg[0])
                except Exception:
                    continue
        else:
            # Fallback: best effort sum if elements are numeric-like
            for x in segments:
                try:
                    total += float(x)
                except Exception:
                    continue
        return total

    def _maybe_reset_episode(self):
        """Detect new episode by elapsed_seconds reset and reinitialize state."""
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if not hasattr(self, "_last_elapsed") or self._last_elapsed is None or elapsed < self._last_elapsed:
            # New episode detected
            self.force_on_demand = False
            self.commit_threshold = None
        self._last_elapsed = elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_episode()

        # Initialize commit_threshold once per episode when env is ready
        gap = float(self.env.gap_seconds)
        if self.commit_threshold is None:
            # Commit threshold must be at least one gap for safety against discretization
            self.commit_threshold = max(gap, float(self.restart_overhead))

        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        restart_overhead = float(self.restart_overhead)

        work_done = self._compute_work_done()
        remaining = max(0.0, float(self.task_duration) - work_done)
        time_left = max(0.0, deadline - elapsed)

        if remaining <= 0.0:
            # Task is done (or effectively done); no need to pay for more compute
            return ClusterType.NONE

        # Margin: extra wall-clock time beyond what is needed to finish
        margin = time_left - (remaining + restart_overhead)

        # If we've already decided to stick with on-demand, keep doing so
        if getattr(self, "force_on_demand", False):
            return ClusterType.ON_DEMAND

        # If margin is small (or negative), we must switch to On-Demand to avoid missing deadline
        if margin <= self.commit_threshold:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Spot-favoring phase: use Spot when available, otherwise wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)