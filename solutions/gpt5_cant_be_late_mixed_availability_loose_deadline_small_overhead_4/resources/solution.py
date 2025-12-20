import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None, *a, **kw):
        super().__init__(*a, **kw)
        self.args = args
        self._locked_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = sum(self.task_done_time) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        remaining = self.task_duration - done
        return remaining if remaining > 0 else 0.0

    def _should_wait_one_step(self, remaining: float, time_budget: float, overhead_if_switch: float, gap: float, guard: float) -> bool:
        # Safe to wait one step if even in worst-case (no progress during next step),
        # we can still switch to OD and finish before deadline.
        return (remaining + overhead_if_switch + guard) <= (time_budget - gap)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we already committed to on-demand, stay on it to avoid extra overheads and ensure determinism.
        if getattr(self, "_locked_to_od", False):
            return ClusterType.ON_DEMAND

        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        time_elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        time_budget = (self.deadline - time_elapsed)

        # If somehow out of budget, do ON_DEMAND to make any possible progress.
        if time_budget <= 0:
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

        remaining = self._remaining_work()
        if remaining <= 0:
            return ClusterType.NONE

        # Overhead if we switch to OD from current state (not OD)
        current_cluster = getattr(self.env, "cluster_type", last_cluster_type)
        overhead_if_switch = 0.0 if current_cluster == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Add a small guard margin to combat discretization and overhead timing effects.
        guard_margin = 0.5 * max(gap, float(self.restart_overhead))

        # Decision logic:
        # Prefer SPOT if available and safe. If SPOT not available, pause if safe, otherwise switch to OD.
        if has_spot:
            # If it's safe to wait a step, use SPOT now.
            if self._should_wait_one_step(remaining, time_budget, overhead_if_switch, gap, guard_margin):
                return ClusterType.SPOT
            # Otherwise, commit to OD to guarantee finishing.
            self._locked_to_od = True
            return ClusterType.ON_DEMAND
        else:
            # No SPOT: if safe to wait (NONE) one step, do so; else switch to OD.
            if self._should_wait_one_step(remaining, time_budget, overhead_if_switch, gap, guard_margin):
                return ClusterType.NONE
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        if parser is None:
            parser = argparse.ArgumentParser()
        # No custom args currently, but keep hook for future configuration.
        args, _ = parser.parse_known_args()
        return cls(args)
