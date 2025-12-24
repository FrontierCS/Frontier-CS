from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            # In case base class doesn't require args or super init signature mismatch
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = sum(self.task_done_time) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = max(0.0, float(self.task_duration) - float(done))
        return remaining

    def _slack(self) -> float:
        # Slack S = (time left to deadline) - (remaining work)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        return time_left - self._remaining_work()

    def _fudge(self) -> float:
        # Small safety margin to account for discretization and modeling mismatch
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 300.0  # default 5 minutes
        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 600.0  # default 10 minutes
        # Use the smaller of gap and ~60% of overhead, but at least 30 seconds
        return max(30.0, min(gap, 0.6 * overhead))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already finished, do nothing
        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Once committed to on-demand, never switch back (safety-first)
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Core parameters
        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 600.0
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 300.0

        fudge = self._fudge()
        slack = self._slack()

        # If we've exhausted safe slack, commit to on-demand
        if slack <= (overhead + fudge):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Spot available
        if has_spot:
            # If already on SPOT, keep using it while slack remains sufficient
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            # Starting SPOT from NONE/ON_DEMAND incurs overhead now; we also
            # want to retain enough slack for a possible future switch to OD.
            # Require slack >= overhead(now to start SPOT) + overhead(later to switch to OD) + fudge
            if slack > (2.0 * overhead + fudge):
                return ClusterType.SPOT
            else:
                # Not enough slack to afford two restarts; commit to OD to guarantee finish
                self._committed_to_od = True
                return ClusterType.ON_DEMAND

        # Spot unavailable: decide to wait (NONE) or commit to on-demand
        # Safe to wait for one step only if after waiting we still have enough slack
        # to immediately switch to OD and finish: slack - gap > overhead + fudge
        if (slack - gap) > (overhead + fudge):
            return ClusterType.NONE

        # Otherwise, commit to OD to guarantee meeting the deadline
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
