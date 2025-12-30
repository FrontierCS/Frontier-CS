import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy using slack-aware Spot preference."""
    NAME = "cb_late_multi_v1"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize strategy from spec file."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Ensure compatibility with possible ClusterType member naming.
        if not hasattr(ClusterType, "NONE") and hasattr(ClusterType, "None"):
            setattr(ClusterType, "NONE", getattr(ClusterType, "None"))

        # Internal state: track cumulative work done efficiently.
        self._progress_done = 0.0
        self._last_task_done_segments = 0

        # Panic threshold margin (seconds) before deadline to switch to OD.
        gap = getattr(self.env, "gap_seconds", 1.0)
        overhead = getattr(self, "restart_overhead", 0.0)
        deadline = getattr(self, "deadline", 0.0)

        # Base margin: at least a few steps or one overhead duration.
        base_margin = max(overhead, 4.0 * gap)
        if deadline > 0.0:
            # Do not be overly conservative; cap at 20% of deadline.
            max_margin = 0.2 * deadline
            self._od_panic_margin = min(base_margin, max_margin)
        else:
            self._od_panic_margin = base_margin

        # Once panic mode is entered, we always use on-demand.
        self._panic_mode = False

        return self

    def _update_progress(self) -> None:
        """Incrementally update total progress from task_done_time."""
        td = self.task_done_time
        idx = self._last_task_done_segments
        if idx < len(td):
            total = 0.0
            for i in range(idx, len(td)):
                total += td[i]
            self._progress_done += total
            self._last_task_done_segments = len(td)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE.
        """
        # Update internal progress accounting.
        self._update_progress()

        # Remaining useful work (seconds).
        remaining_work = self.task_duration - self._progress_done
        if remaining_work <= 0.0:
            # Task already completed.
            return ClusterType.NONE

        # Time remaining until deadline (seconds).
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Past deadline; use OD to minimize further delay.
            return ClusterType.ON_DEMAND

        # In panic mode, always use on-demand to guarantee completion.
        if self._panic_mode:
            return ClusterType.ON_DEMAND

        # Compute minimal time needed to finish if we switch to OD now
        # and then stay on OD until completion.
        if last_cluster_type == ClusterType.ON_DEMAND:
            # If already on OD, only remaining_restart_overhead still to be served.
            overhead_to_od = getattr(self, "remaining_restart_overhead", 0.0)
        else:
            # Switching from any other type to OD incurs full restart overhead.
            overhead_to_od = self.restart_overhead

        time_needed_od = remaining_work + overhead_to_od
        slack_for_od = time_left - time_needed_od

        # If slack is small, enter panic mode and commit to on-demand.
        if slack_for_od <= self._od_panic_margin:
            self._panic_mode = True
            return ClusterType.ON_DEMAND

        # Spot-preferred phase: use Spot when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and plenty of slack left: pause to save cost.
        return ClusterType.NONE