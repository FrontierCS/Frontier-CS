import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and spot savings."""

    NAME = "cbmrs_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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

        # Internal accumulators
        self._acc_initialized = False
        self._segments_prev = 0
        self._work_done = 0.0  # in seconds
        self._force_on_demand = False  # once True, stay on on-demand forever

        return self

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _update_work_done(self) -> None:
        """Incrementally track total work done from task_done_time list."""
        if not self._acc_initialized:
            segs = self.task_done_time
            self._segments_prev = len(segs)
            self._work_done = float(sum(segs)) if segs else 0.0
            self._acc_initialized = True
            return

        segs = self.task_done_time
        n = len(segs)
        if n > self._segments_prev:
            total_new = 0.0
            for i in range(self._segments_prev, n):
                total_new += segs[i]
            self._work_done += total_new
            self._segments_prev = n

    # --------------------------------------------------------------------- #
    # Core decision logic
    # --------------------------------------------------------------------- #

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update internal progress estimate
        self._update_work_done()

        # If task is done (or slightly over due to rounding), stop computing
        if self._work_done >= self.task_duration - 1e-6:
            return ClusterType.NONE

        now = self.env.elapsed_seconds
        remaining_work = self.task_duration - self._work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        # Once we commit to on-demand, never go back to spot (avoid extra overhead/risk)
        if not self._force_on_demand:
            gap = self.env.gap_seconds
            # Conservative safety margin:
            #   - allow at most one more "risky" step (which may waste up to gap+overhead time),
            #   - then switch to on-demand and pay up to another restart_overhead before
            #     finishing remaining_work without further interruptions.
            #
            # Upper bound on completion time if we risk one more step:
            #   T_finish <= now + gap + 2*restart_overhead + remaining_work
            #
            # We must ensure this is <= deadline to take that risk.
            conservative_finish_time = (
                now + gap + 2.0 * self.restart_overhead + remaining_work
            )
            if conservative_finish_time > self.deadline:
                self._force_on_demand = True

        if self._force_on_demand:
            # Deterministic, interruption-free path to meet the deadline.
            return ClusterType.ON_DEMAND

        # Spot-preferred phase: use Spot when available, otherwise idle cheaply.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE