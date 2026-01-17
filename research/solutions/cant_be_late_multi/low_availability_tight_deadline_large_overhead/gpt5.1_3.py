import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

    NAME = "my_strategy"

    def __init__(self):
        # Delay base-class initialization until solve() is called.
        # Initialize our own attributes.
        self.num_regions = 0
        self.region_total = []
        self.region_spot = []

        self.commit_to_on_demand = False

        self._progress_done = 0.0
        self._last_tdt_len = 0

        self._task_duration = 0.0
        self._deadline = 0.0
        self._restart_overhead = 0.0
        self._gap = 1.0

        self.alpha = 1.0

        # Cached ClusterType members for robustness
        self.CT_SPOT = getattr(ClusterType, "SPOT", None)
        self.CT_ON_DEMAND = getattr(ClusterType, "ON_DEMAND", None)
        self.CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))

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

        # Initialize local parameters in seconds.
        # MultiRegionStrategy is expected to convert hours->seconds.
        self._task_duration = float(self.task_duration)
        self._deadline = float(self.deadline)
        self._restart_overhead = float(self.restart_overhead)
        self._gap = float(getattr(self.env, "gap_seconds", 1.0))

        # Region statistics.
        if hasattr(self.env, "get_num_regions"):
            self.num_regions = int(self.env.get_num_regions())
        else:
            self.num_regions = 1
        self.region_total = [0] * self.num_regions
        self.region_spot = [0] * self.num_regions

        # Progress tracking.
        self._progress_done = 0.0
        self._last_tdt_len = 0
        self.commit_to_on_demand = False

        return self

    def _update_progress(self):
        """Incrementally maintain total completed work time."""
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, (list, tuple)):
            # Fallback: treat as scalar total progress if provided.
            if tdt is not None:
                self._progress_done = float(tdt)
            return

        n = len(tdt)
        if n > self._last_tdt_len:
            # Sum only new segments.
            for i in range(self._last_tdt_len, n):
                self._progress_done += float(tdt[i])
            self._last_tdt_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region statistics for the current timestep.
        if hasattr(self.env, "get_current_region"):
            curr_region = self.env.get_current_region()
        else:
            curr_region = 0

        if 0 <= curr_region < len(self.region_total):
            self.region_total[curr_region] += 1
            if has_spot:
                self.region_spot[curr_region] += 1

        # Update total progress done so far.
        self._update_progress()

        remaining_work = self._task_duration - self._progress_done
        if remaining_work <= 0:
            # Task finished; no need to run more.
            return self.CT_NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = self._deadline - now
        if remaining_time <= 0:
            # Already past deadline; avoid incurring extra cost.
            return self.CT_NONE

        gap = self._gap
        O = self._restart_overhead

        # Degenerate case: no meaningful gap size.
        if gap <= 0:
            if not self.commit_to_on_demand:
                self.commit_to_on_demand = True
            return self.CT_ON_DEMAND

        # Worst-case ON-DEMAND time from a fresh restart (in seconds).
        steps_needed = math.ceil((remaining_work + O) / gap)
        T_needed = steps_needed * gap

        # Decide whether it's time to permanently switch to ON_DEMAND.
        if not self.commit_to_on_demand:
            # Be conservative: allow at most one more step of delay before fallback.
            if remaining_time <= T_needed + gap:
                self.commit_to_on_demand = True

        if self.commit_to_on_demand:
            # Hard guarantee phase: always use ON_DEMAND to avoid missing deadline.
            return self.CT_ON_DEMAND

        # Pre-fallback phase: only use SPOT or NONE (no ON_DEMAND yet).

        if has_spot and self.CT_SPOT is not None:
            # Spot is currently available in this region; exploit it.
            return self.CT_SPOT

        # Spot not available in the current region: choose NONE and potentially
        # switch to a better region for future steps based on observed statistics.
        if self.num_regions > 1 and hasattr(self.env, "switch_region"):
            curr_region = self.env.get_current_region()
            next_region = curr_region

            # Explore any region that has never been observed.
            unexplored_region = None
            for i in range(self.num_regions):
                if self.region_total[i] == 0:
                    unexplored_region = i
                    break

            if unexplored_region is not None:
                next_region = unexplored_region
            else:
                # All regions visited; choose region with highest estimated spot availability.
                alpha = self.alpha
                best_region = curr_region
                best_score = (self.region_spot[curr_region] + alpha) / (
                    self.region_total[curr_region] + 2.0 * alpha
                )
                for i in range(self.num_regions):
                    score = (self.region_spot[i] + alpha) / (
                        self.region_total[i] + 2.0 * alpha
                    )
                    if score > best_score + 1e-8:
                        best_score = score
                        best_region = i
                next_region = best_region

            if next_region != curr_region:
                self.env.switch_region(next_region)

        return self.CT_NONE