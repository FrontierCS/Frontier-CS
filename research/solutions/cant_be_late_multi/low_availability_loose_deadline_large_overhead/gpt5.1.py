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
        self._internal_state_initialized = False
        return self

    def _initialize_internal_state(self) -> None:
        self._internal_state_initialized = True
        self._last_elapsed_seconds = self.env.elapsed_seconds

        segments = self.task_done_time
        total = 0.0
        for v in segments:
            total += v
        self._total_work_done = total
        self._last_total_work_done = total
        self._last_segments_len = len(segments)

        self.spot_time_total = 0.0
        self.spot_progress_total = 0.0

        self.committed_to_on_demand = False
        self.disable_spot = False

        # Minimum Spot run time (seconds) before we trust efficiency estimates
        self.min_spot_sample_time = max(2.0 * self.env.gap_seconds, 0.1 * self.task_duration)

        # SPOT efficiency threshold: below this, Spot is not cost-effective vs on-demand
        # Based on price ratio ~0.97 / 3.06 ≈ 0.317, with safety margin.
        self.spot_efficiency_threshold = 0.35

    def _update_counters(self, last_cluster_type: ClusterType) -> None:
        cur_time = self.env.elapsed_seconds
        dt = cur_time - self._last_elapsed_seconds
        if dt < 0.0:
            dt = 0.0
        self._last_elapsed_seconds = cur_time

        segments = self.task_done_time
        n = len(segments)
        if n > self._last_segments_len:
            added = 0.0
            for i in range(self._last_segments_len, n):
                added += segments[i]
            self._total_work_done += added
            self._last_segments_len = n

        cur_total_work = self._total_work_done
        dwork = cur_total_work - self._last_total_work_done
        if dwork < 0.0:
            dwork = 0.0
        self._last_total_work_done = cur_total_work

        if last_cluster_type == ClusterType.SPOT and dt > 0.0:
            self.spot_time_total += dt
            if dwork > 0.0:
                self.spot_progress_total += dwork

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self._internal_state_initialized:
            self._initialize_internal_state()
        else:
            self._update_counters(last_cluster_type)

        remaining_work = self.task_duration - self._total_work_done
        if remaining_work <= 0.0:
            self.committed_to_on_demand = True
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to on-demand to guarantee meeting the deadline
        if not self.committed_to_on_demand:
            dt_max = self.env.gap_seconds + self.restart_overhead
            safe_threshold = remaining_work + self.restart_overhead + dt_max
            if time_left <= safe_threshold:
                self.committed_to_on_demand = True

        # Optionally disable Spot if observed efficiency is too low
        if (not self.disable_spot) and self.spot_time_total >= self.min_spot_sample_time:
            if self.spot_time_total > 0.0:
                efficiency = self.spot_progress_total / self.spot_time_total
            else:
                efficiency = 0.0
            if efficiency < self.spot_efficiency_threshold:
                self.disable_spot = True

        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        if self.disable_spot or not has_spot:
            return ClusterType.NONE

        return ClusterType.SPOT