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
        return self

    # -------- Internal helpers --------

    def _initialize_internal_state(self):
        """Lazy initialization once env is ready."""
        self._internal_initialized = True

        # Region statistics for Spot availability
        num_regions = self.env.get_num_regions()
        self.num_regions = num_regions
        self.region_total_steps = [0] * num_regions
        self.region_spot_steps = [0] * num_regions
        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        self.region_last_spot_time = [now] * num_regions

        # Track cumulative task progress without summing list every step
        self._last_task_done_len = len(getattr(self, "task_done_time", []))
        if self._last_task_done_len > 0:
            self._cumulative_task_done = float(sum(self.task_done_time))
        else:
            self._cumulative_task_done = 0.0

        # Control flags
        self.force_on_demand = False

        # Time buffers (seconds)
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        # Ensure force buffer at least one step and one overhead
        self.force_on_demand_buffer = max(gap, restart_overhead)
        # We only wait for Spot (NONE actions) while we have plenty of slack
        self.wait_spot_buffer = 3.0 * self.force_on_demand_buffer + restart_overhead

    def _update_task_progress(self):
        """Incrementally track total completed work time."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_done_len:
            new_sum = sum(self.task_done_time[self._last_task_done_len : current_len])
            self._cumulative_task_done += float(new_sum)
            self._last_task_done_len = current_len

    def _select_best_region(self, current_region: int) -> int:
        """Pick region with highest empirical Spot availability (with simple prior)."""
        if self.num_regions <= 1:
            return current_region

        best_idx = current_region
        best_score = -1.0
        for i in range(self.num_regions):
            total = self.region_total_steps[i]
            spot = self.region_spot_steps[i]
            # Beta(1,1) prior -> (spot + 1) / (total + 2)
            score = (spot + 1.0) / (total + 2.0)
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    # -------- Core decision logic --------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization when env is fully available
        if not getattr(self, "_internal_initialized", False):
            self._initialize_internal_state()

        # Update cumulative completed work
        self._update_task_progress()

        # Compute remaining work and time
        remaining_work = self.task_duration - self._cumulative_task_done
        if remaining_work <= 0.0:
            # Task already finished; no need to run anything
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        if remaining_time <= 0.0:
            # Past deadline; nothing we do now affects score positively
            return ClusterType.NONE

        cur_region = self.env.get_current_region()

        # Update per-region Spot statistics
        if 0 <= cur_region < self.num_regions:
            self.region_total_steps[cur_region] += 1
            if has_spot:
                self.region_spot_steps[cur_region] += 1
                self.region_last_spot_time[cur_region] = self.env.elapsed_seconds

        # If we've already committed to On-Demand, keep using it
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Time needed to finish if we start On-Demand now:
        # remaining_work plus one restart overhead for switching to OD.
        ond_needed = remaining_work + self.restart_overhead
        slack = remaining_time - ond_needed

        # If even starting OD now is tight or impossible, switch immediately
        if slack <= 0.0:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # When slack is small, we must not risk Spot or waiting
        if slack <= self.force_on_demand_buffer:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are in the "Spot phase": enough slack to safely exploit Spot
        if has_spot:
            # Run on Spot when available
            return ClusterType.SPOT

        # No Spot available in current region
        if slack >= self.wait_spot_buffer:
            # Plenty of slack: wait (NONE) and move to a better region for next step
            next_region = self._select_best_region(cur_region)
            if next_region != cur_region:
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Moderate slack but not enough to keep waiting for Spot:
        # fall back to On-Demand from now on.
        self.force_on_demand = True
        return ClusterType.ON_DEMAND