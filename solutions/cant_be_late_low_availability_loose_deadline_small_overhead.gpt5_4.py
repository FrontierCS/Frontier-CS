import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbt_threshold_waiter_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_od = False
        self._done_sum = 0.0
        self._done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_done_sum(self):
        tlist = getattr(self, "task_done_time", None)
        if tlist is None:
            return
        n = len(tlist)
        if n < self._done_len:
            # Recompute if list replaced with shorter one (shouldn't happen, but be safe)
            self._done_sum = sum(tlist)
            self._done_len = n
        elif n > self._done_len:
            self._done_sum += sum(tlist[self._done_len:n])
            self._done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        # Time units are seconds
        s = float(self.env.gap_seconds)
        oh = float(self.restart_overhead)
        T = max(float(self.deadline) - float(self.env.elapsed_seconds), 0.0)
        R = max(float(self.task_duration) - float(self._done_sum), 0.0)
        EPS = 1e-9

        if R <= EPS:
            return ClusterType.NONE

        # If we already committed to on-demand, stick to it unless we can finish immediately on spot
        if self._commit_od:
            if has_spot and R <= s + EPS:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Not committed yet: decide based on safety thresholds
        if has_spot:
            # If we can finish within this step on spot, do it
            if R <= s + EPS:
                return ClusterType.SPOT
            # Safe to use spot now if, even with a preemption after this step, we can finish by deadline
            # Condition: T >= R + oh
            if T >= R + oh + EPS:
                return ClusterType.SPOT
            # Otherwise, switch to OD and commit
            self._commit_od = True
            return ClusterType.ON_DEMAND
        else:
            # Spot unavailable: wait if we can afford waiting one more step and still finish after a restart overhead
            # Condition to wait this step: T - s >= R + oh  -> T >= R + oh + s
            if T >= R + oh + s + EPS:
                return ClusterType.NONE
            # Otherwise, switch to OD and commit
            self._commit_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        if not isinstance(parser, argparse.ArgumentParser):
            parser = argparse.ArgumentParser()
        args, _ = parser.parse_known_args()
        return cls(args)
