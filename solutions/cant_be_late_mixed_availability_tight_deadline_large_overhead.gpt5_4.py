from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import argparse

class Solution(Strategy):
    NAME = "wait_spot_last_safe_od"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            super().__init__()
        # Configurable safety fudge multiplier relative to gap_seconds
        self._fudge_mult = 0.0
        if args is not None and hasattr(args, "fudge_mult"):
            try:
                self._fudge_mult = float(args.fudge_mult)
            except Exception:
                self._fudge_mult = 0.0
        self._lock_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self):
        done = 0.0
        try:
            if self.task_done_time:
                done = float(sum(self.task_done_time))
        except Exception:
            done = 0.0
        rem = max(0.0, float(self.task_duration) - done)
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Persist with on-demand once we commit (reduces risk near deadline)
        if self._lock_on_demand:
            # If completed, stop
            if self._remaining_work() <= 0.0:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        t = float(self.env.elapsed_seconds)
        g = float(self.env.gap_seconds)
        D = float(self.deadline)
        O = float(self.restart_overhead)
        R = self._remaining_work()

        if R <= 0.0:
            return ClusterType.NONE

        fudge = self._fudge_mult * g
        # Latest safe time considering an immediate restart overhead if we need to start computing
        Lprime = D - R - O - fudge

        # If time is beyond safe threshold, immediately switch to on-demand and lock
        if t > Lprime:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # If Spot is available and safe to run this step, use Spot
        if has_spot:
            # Safe to spend this step on Spot; even if Spot disappears next step,
            # we can still switch to OD with overhead and finish by D.
            # Condition: t + O + R <= D (i.e., t <= Lprime)
            if t <= Lprime:
                return ClusterType.SPOT
            # Otherwise we must secure completion now on OD
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # Spot not available: decide to wait or switch to OD
        # Safe to wait this step only if starting OD next step (with overhead) still finishes
        # i.e., t + g + O + R <= D  -> t <= Lprime - g
        if t <= Lprime - g:
            return ClusterType.NONE

        # Not safe to wait any longer; must switch to OD now and lock
        self._lock_on_demand = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        if not isinstance(parser, argparse.ArgumentParser):
            parser = argparse.ArgumentParser()
        parser.add_argument("--fudge-mult", type=float, default=0.0, help="Safety margin multiplier on gap_seconds.")
        args, _ = parser.parse_known_args()
        return cls(args)
