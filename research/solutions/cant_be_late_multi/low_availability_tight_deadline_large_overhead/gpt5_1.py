import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state
        self._committed_to_od = False
        self._od_commit_margin_seconds = None
        return self

    def _compute_commit_margin(self) -> float:
        # Set a conservative margin to absorb discrete time steps and potential overheads
        # Use max of:
        # - 3 * restart_overhead
        # - 3 * gap_seconds
        # - 3600 seconds (1 hour)
        # Cap not necessary; keep simple and safe.
        gap = getattr(self.env, "gap_seconds", 300.0)
        ro = getattr(self, "restart_overhead", 900.0)
        base = max(3.0 * ro, 3.0 * gap, 3600.0)
        return base

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize margin lazily when env is ready
        if self._od_commit_margin_seconds is None:
            self._od_commit_margin_seconds = self._compute_commit_margin()

        # If already committed to On-Demand, just keep running OD to avoid restarts.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Gather timing information
        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline - elapsed)
        done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        remaining_work = max(0.0, float(self.task_duration - done))

        # If no work remains, don't launch anything.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Remaining restart overhead currently pending (if any)
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))

        # Time required to finish if we commit to OD now:
        # - If we're already on OD, we only need to account current pending overhead.
        # - Otherwise, switching to OD incurs a fresh restart overhead.
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_now = pending_overhead
        else:
            od_overhead_now = float(self.restart_overhead)

        time_needed_if_od_now = od_overhead_now + remaining_work

        # If even switching to OD now cannot meet the deadline, we still choose OD as best effort.
        if time_left <= time_needed_if_od_now:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Compute how long we can wait before we must switch to OD to still finish on time.
        # This is our slack buffer before committing to OD.
        spare_time_if_switch_now = time_left - time_needed_if_od_now

        # If our spare time is below the margin, commit to OD to ensure completion.
        if spare_time_if_switch_now <= self._od_commit_margin_seconds:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can still afford to try Spot
        if has_spot:
            return ClusterType.SPOT

        # No Spot available, but we have buffer: wait (NONE) to avoid unnecessary OD cost/overheads.
        return ClusterType.NONE