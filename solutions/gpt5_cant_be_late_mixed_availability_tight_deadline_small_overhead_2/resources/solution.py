from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "jit_od_fallback_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.commit_to_od: bool = False
        self._last_reset_marker: Optional[int] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self) -> float:
        try:
            return float(sum(self.task_done_time))
        except Exception:
            return 0.0

    def _reset_check(self):
        # Reset state at the start of each new episode/run
        # Detect new run by checking if elapsed_seconds is 0 or decreasing (environment reset)
        if self._last_reset_marker is None or self.env.elapsed_seconds < (self._last_reset_marker or 0) or self.env.elapsed_seconds <= 0:
            self.commit_to_od = False
        self._last_reset_marker = self.env.elapsed_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_check()

        # If we are already on OD, commit to stay on OD to avoid unnecessary switches.
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            self.commit_to_od = True

        remaining = max(0.0, self.task_duration - self._sum_done())
        if remaining <= 0.0:
            return ClusterType.NONE

        if self.commit_to_od:
            return ClusterType.ON_DEMAND

        t = float(self.env.elapsed_seconds)
        g = float(self.env.gap_seconds)
        d = float(self.deadline)
        overhead = float(self.restart_overhead)

        # Latest safe time to start OD to finish on time (including restart overhead)
        latest_start_od = d - (remaining + overhead)

        # Small safety margin to avoid off-by-one timestep rounding issues
        fudge = min(max(g * 0.5, 0.0), 30.0)

        # If we're at or past the latest time to safely switch (with margin), switch to OD now.
        if t + fudge >= latest_start_od:
            self.commit_to_od = True
            return ClusterType.ON_DEMAND

        # Spot unavailable: wait if still safe; otherwise switch to OD
        if not has_spot:
            if t + g + fudge <= latest_start_od:
                return ClusterType.NONE
            else:
                self.commit_to_od = True
                return ClusterType.ON_DEMAND

        # Spot is available:
        # Use spot if we can safely wait one more step and still be able to fall back to OD next step.
        if t + g + fudge <= latest_start_od:
            return ClusterType.SPOT
        else:
            # Not safe to rely on spot for another step; switch to OD now.
            self.commit_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
