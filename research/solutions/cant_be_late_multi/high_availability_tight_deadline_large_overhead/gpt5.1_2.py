import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee."""
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

        # Internal state initialization (deferred finalization to first _step call).
        self._strategy_initialized = False
        return self

    # ---- Internal helpers -------------------------------------------------

    def _initialize_strategy(self):
        """Initialize strategy parameters once environment is available."""
        if self._strategy_initialized:
            return
        self._strategy_initialized = True

        # Task/work accounting
        self._work_done = 0.0
        self._last_task_done_index = len(self.task_done_time)
        if self._last_task_done_index > 0:
            # Should be zero at start, but support robustness.
            self._work_done = float(sum(self.task_done_time))

        # Handle possible list/scalar representations for restart_overhead/task_duration.
        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        else:
            self._task_duration = float(td)

        self._gap = float(getattr(self.env, "gap_seconds", 0.0))
        self._deadline = float(self.deadline)

        # Commit-to-on-demand threshold:
        # Chosen to ensure that even in a worst-case single additional Spot attempt
        # (lost work + overhead), we still have enough slack to pay one restart overhead.
        l_max = 2.0 * self._gap + self._restart_overhead  # worst slack loss from one Spot attempt
        base_threshold = l_max + self._restart_overhead
        # Also keep a minimum of several overheads as slack for robustness.
        min_threshold = 6.0 * self._restart_overhead
        self._commit_slack_threshold = max(base_threshold, min_threshold)

        # Once set, we never go back to Spot.
        self._force_on_demand = False

        # Multi-region: simple round-robin when idle and Spot unavailable.
        self._num_regions = int(getattr(self.env, "get_num_regions", lambda: 1)())
        if self._num_regions <= 0:
            self._num_regions = 1

    def _update_work_done(self):
        """Incrementally track total work done to avoid O(n^2) summations."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_done_index:
            # Sum only new segments.
            new_segments = self.task_done_time[self._last_task_done_index:current_len]
            if new_segments:
                self._work_done += float(sum(new_segments))
            self._last_task_done_index = current_len

    # ---- Main decision function -------------------------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._strategy_initialized:
            self._initialize_strategy()

        # Update accumulated work.
        self._update_work_done()

        elapsed = float(self.env.elapsed_seconds)
        remaining_work = max(0.0, self._task_duration - self._work_done)
        remaining_time = max(0.0, self._deadline - elapsed)

        # If task is already complete or no time left, don't run anything.
        if remaining_work <= 0.0 or remaining_time <= 0.0:
            return ClusterType.NONE

        # Current slack: time we can still afford to waste (overheads, idling, lost work).
        slack = remaining_time - remaining_work
        if slack < 0.0:
            slack = 0.0  # numerical guard

        # If we've already decided to use On-Demand only, stick with it.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Hard safety: if even with immediate switch to On-Demand we're near the edge,
        # force On-Demand now.
        min_time_needed_od = self._restart_overhead + remaining_work
        if remaining_time <= min_time_needed_od:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Commit rule based on remaining slack.
        if slack <= self._commit_slack_threshold:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Flexible phase: prefer Spot; idle when Spot unavailable.
        if has_spot:
            # Favor Spot while we still have comfortable slack.
            return ClusterType.SPOT

        # No Spot in current region and we are still in flexible phase.
        # Idle and (optionally) explore other regions in a round-robin fashion,
        # but avoid wasting any in-progress restart overhead.
        if self._num_regions > 1 and self.remaining_restart_overhead <= 0.0:
            try:
                current_region = int(self.env.get_current_region())
                next_region = (current_region + 1) % self._num_regions
                # Switch region for the next timestep.
                self.env.switch_region(next_region)
            except Exception:
                # Be robust to any unexpected env issues; simply don't switch.
                pass

        return ClusterType.NONE