import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for efficient progress tracking and policy control.
        self.committed_to_on_demand = False
        self._cached_work_done = 0.0
        self._last_task_done_index = 0

        return self

    def _update_work_done(self) -> None:
        """Incrementally update cached work done to avoid O(n) sums each step."""
        lst = self.task_done_time
        idx = self._last_task_done_index
        if idx < len(lst):
            # Only sum newly added segments.
            self._cached_work_done += sum(lst[idx:])
            self._last_task_done_index = len(lst)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Efficiently track total work completed so far.
        self._update_work_done()
        work_done = self._cached_work_done

        remaining_work = self.task_duration - work_done
        if remaining_work <= 0.0:
            # Task finished; no need to run more.
            self.committed_to_on_demand = True
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed

        # If for some reason we're at/after deadline but not done, use on-demand.
        if time_remaining <= 0.0:
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Once committed, always run on-demand to avoid further restarts.
        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        # Conservative assumption: switching to on-demand later will incur
        # at most one restart overhead.
        commit_overhead = self.restart_overhead

        # Time left after taking one "risky" step that might yield zero progress.
        time_after_risky = time_remaining - gap

        # If even one step doesn't fit cleanly, must use on-demand now.
        if time_after_risky < 0.0:
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Safe-to-wait check:
        # After possibly wasting this step (0 progress), we still must be able
        # to finish using pure on-demand with one restart overhead.
        if time_after_risky >= remaining_work + commit_overhead:
            # Still safe to take risk this step.
            if has_spot:
                return ClusterType.SPOT
            else:
                # No spot now; safe to idle and wait for cheaper spot later.
                return ClusterType.NONE
        else:
            # Not safe anymore to risk; commit to on-demand from now on.
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND