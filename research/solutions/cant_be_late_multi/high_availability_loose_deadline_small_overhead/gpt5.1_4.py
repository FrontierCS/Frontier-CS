import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy using slack-based Spot vs On-Demand control."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for efficient progress tracking and policy
        self._work_done = 0.0
        self._tdt_len = 0
        self._committed_to_on_demand = False

        # Start from a fixed region (0) for determinism; ignore failures if not supported.
        try:
            if hasattr(self, "env"):
                current_region = self.env.get_current_region()
                if current_region != 0:
                    self.env.switch_region(0)
        except Exception:
            pass

        return self

    def _update_progress_cache(self) -> None:
        """Incrementally maintain total work_done from task_done_time list."""
        tdt = self.task_done_time
        n = len(tdt)
        if n > self._tdt_len:
            # Add only newly appended segments
            total = self._work_done
            for i in range(self._tdt_len, n):
                total += tdt[i]
            self._work_done = total
            self._tdt_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        # Refresh cached work_done
        self._update_progress_cache()

        # Basic quantities (seconds)
        task_duration = self.task_duration
        restart_overhead = self.restart_overhead
        gap = self.env.gap_seconds

        # Remaining work
        remaining_work = max(task_duration - self._work_done, 0.0)

        # If already finished, ensure we don't run unnecessarily
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time left until deadline
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If we've somehow passed the deadline but not done, just run On-Demand
        # (penalty is already inevitable, but this is the only sensible action).
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # If we've already committed to On-Demand, always keep running it.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Slack margin over the minimum required time if we were to switch to OD now:
        # margin = time_left - (remaining_work + restart_overhead)
        # We must keep this non-negative to have a feasible guaranteed schedule.
        margin = time_left - (remaining_work + restart_overhead)

        # Decide whether to commit to On-Demand now, using a conservative
        # bound on the "wasted" time of the next step if we keep using Spot/NONE.
        #
        # waste = elapsed_time_this_step - progress_this_step >= 0
        # For action NONE:    worst waste = gap
        # For action SPOT:    worst waste <= gap + restart_overhead
        # We choose the action-specific bound to ensure we never cross margin < 0
        # without first committing to On-Demand.
        if has_spot:
            waste_bound = gap + restart_overhead
        else:
            waste_bound = gap

        # If margin is already very small, or negative due to numerical/edge cases,
        # commit immediately.
        if margin <= 0.0 or margin < waste_bound:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Still in safe slack region and not yet committed:
        # - Use Spot when available.
        # - Otherwise, wait (NONE) to save cost, relying on future Spot or
        #   eventual On-Demand commitment when slack shrinks.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE