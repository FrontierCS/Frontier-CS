import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline-aware Spot/On-Demand switching."""

    NAME = "cbl_multi_region_v1"

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

        # Lazy runtime initialization flag.
        self._initialized = False
        return self

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _lazy_init(self):
        """Initialize runtime state on first _step call."""
        if self._initialized:
            return
        self._initialized = True

        # Task duration and restart overhead as floats (seconds).
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            self._task_total_work = float(td[0])
        else:
            self._task_total_work = float(td)

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        # Cached completed work to avoid O(n^2) summations.
        self._cached_done_work = 0.0
        self._cached_segments = 0
        if hasattr(self, "task_done_time") and self.task_done_time:
            self._cached_segments = len(self.task_done_time)
            # Only once on init; list initially is small.
            self._cached_done_work = float(sum(self.task_done_time))

        # Force using On-Demand from some point onward.
        self._force_on_demand = False

        # Step counter.
        self._step_idx = 0

        # Region statistics for (very lightweight) multi-region behavior.
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        self._num_regions = int(num_regions) if num_regions is not None else 1
        if self._num_regions <= 0:
            self._num_regions = 1

        self._region_steps = [0] * self._num_regions
        self._region_spot_up = [0.0] * self._num_regions
        self._region_consec_down = [0] * self._num_regions
        self._last_switch_step = -10**9  # effectively "never"
        self._min_switch_interval_steps = 30  # avoid thrashing

    # ------------------------------------------------------------------ #
    # Core decision logic
    # ------------------------------------------------------------------ #

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._lazy_init()
        self._step_idx += 1

        # Update cached completed work if new segments have appeared.
        segments = self.task_done_time
        seg_len = len(segments)
        if seg_len > self._cached_segments:
            # At most one new segment per step; but handle general case safely.
            inc = 0.0
            for v in segments[self._cached_segments:seg_len]:
                inc += float(v)
            self._cached_done_work += inc
            self._cached_segments = seg_len

        remaining_work = self._task_total_work - self._cached_done_work
        if remaining_work <= 0.0:
            # Task finished; no need to run more.
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        slack = self.deadline - elapsed
        if slack <= 0.0:
            # Already past deadline; best effort is to finish ASAP on On-Demand.
            self._force_on_demand = True

        gap = getattr(self.env, "gap_seconds", 1.0)

        # Update per-region statistics.
        try:
            curr_region = self.env.get_current_region()
        except Exception:
            curr_region = 0
        if curr_region < 0 or curr_region >= self._num_regions:
            curr_region = 0
        self._region_steps[curr_region] += 1
        if has_spot:
            self._region_spot_up[curr_region] += 1.0
            self._region_consec_down[curr_region] = 0
        else:
            self._region_consec_down[curr_region] += 1

        # Decide whether we must commit to On-Demand from now on.
        if not self._force_on_demand:
            # Margin accounts for one restart overhead and a couple of time steps.
            margin_time = self._restart_overhead + 2.0 * gap
            if slack <= remaining_work + margin_time:
                self._force_on_demand = True

        # If we've committed, always use On-Demand.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet forced onto On-Demand: we prefer Spot where possible.

        # Case 1: Spot available in current region.
        if has_spot:
            return ClusterType.SPOT

        # Case 2: Spot not available. Decide between waiting (NONE), switching
        # region, or (early) switching to On-Demand if we can't wait safely.

        # Check if we can safely afford to wait one more gap without breaking
        # the ability to finish on On-Demand with a single restart overhead.
        if slack - gap > remaining_work + self._restart_overhead:
            # Enough slack to wait; try to be in a good region and idle this step.
            if self._num_regions > 1 and (
                self._step_idx - self._last_switch_step >= self._min_switch_interval_steps
            ):
                # Choose region with highest empirical Spot availability (with prior).
                best_region = curr_region
                best_score = -1.0
                for r in range(self._num_regions):
                    steps_r = self._region_steps[r]
                    if steps_r == 0:
                        score = 0.6  # optimistic prior for unseen regions
                    else:
                        score = self._region_spot_up[r] / steps_r
                    if score > best_score:
                        best_score = score
                        best_region = r

                steps_curr = self._region_steps[curr_region]
                if steps_curr == 0:
                    curr_score = 0.6
                else:
                    curr_score = self._region_spot_up[curr_region] / steps_curr

                if best_region != curr_region and best_score >= curr_score + 0.05:
                    self.env.switch_region(best_region)
                    self._last_switch_step = self._step_idx

            # Wait this step to save cost; rely on Spot later.
            return ClusterType.NONE

        # Can't afford to wait longer; commit to On-Demand immediately.
        self._force_on_demand = True
        return ClusterType.ON_DEMAND