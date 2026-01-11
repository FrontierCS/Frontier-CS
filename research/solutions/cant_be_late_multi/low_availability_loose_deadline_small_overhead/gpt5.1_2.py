import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy implementing a slack-based policy."""

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

        # Internal state (initialized lazily once env is attached)
        self._initialized_internal_state = False
        return self

    # ---- Internal helpers ----

    def _init_internal_state(self):
        """Lazily initialize internal parameters once env is available."""
        self._initialized_internal_state = True

        # Gap (seconds per step)
        gap = getattr(self.env, "gap_seconds", 1.0)
        self._gap = float(gap)

        # restart_overhead and others are in seconds per specification
        self.restart_overhead = float(self.restart_overhead)

        # Safety margins (seconds)
        # Enough to cover a couple of restart overheads plus several steps.
        self._safety_margin = max(2.0 * self.restart_overhead, 5.0 * self._gap)
        # Extra slack before we stop idling (ClusterType.NONE) when spot is down.
        self._none_slack_threshold = max(self.restart_overhead, 5.0 * self._gap)

        # Region-switching thresholds (for multi-region exploration)
        # Switch if we've seen no spot for a while in current region.
        self._region_switch_unavailable_threshold = max(
            4.0 * self.restart_overhead, 10.0 * self._gap
        )
        self._region_switch_cooldown = self._region_switch_unavailable_threshold

        # Tracking variables
        self._no_spot_time_in_region = 0.0
        self._last_region_switch_time = 0.0
        self._committed_to_on_demand = False

        # Cache sum(task_done_time) for O(1) per-step updates
        self._cached_task_done_sum = 0.0
        self._cached_task_done_len = 0

        # Scalar task duration and deadline, guarding against list types
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration_scalar = float(td[0]) if td else 0.0
        elif td is None:
            self._task_duration_scalar = 0.0
        else:
            self._task_duration_scalar = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            self._deadline_scalar = float(dl[0]) if dl else 0.0
        elif dl is None:
            self._deadline_scalar = 0.0
        else:
            self._deadline_scalar = float(dl)

    def _update_task_done_cache(self) -> float:
        """Update cached sum(self.task_done_time) efficiently."""
        lst = self.task_done_time
        length = len(lst)
        if length < self._cached_task_done_len:
            # List was reset; recompute from scratch.
            self._cached_task_done_sum = sum(lst)
            self._cached_task_done_len = length
        elif length > self._cached_task_done_len:
            # New segments appended; only sum the new tail.
            new_segments = lst[self._cached_task_done_len :]
            if new_segments:
                self._cached_task_done_sum += sum(new_segments)
            self._cached_task_done_len = length
        return self._cached_task_done_sum

    # ---- Core decision logic ----

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_initialized_internal_state", False):
            self._init_internal_state()

        # Compute remaining work
        done = self._update_task_done_cache()
        remaining_work = self._task_duration_scalar - done

        # If task already done, no need to run anything.
        if remaining_work <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.NONE

        time_elapsed = float(self.env.elapsed_seconds)
        time_remaining = self._deadline_scalar - time_elapsed

        # If we've already exceeded the deadline, keep using ON_DEMAND to at least finish.
        if time_remaining <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Estimate time needed to finish if we switch/stick to ON_DEMAND now.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_commit = float(getattr(self, "remaining_restart_overhead", 0.0))
            if overhead_commit < 0.0:
                overhead_commit = 0.0
        else:
            overhead_commit = self.restart_overhead

        time_needed_od = remaining_work + overhead_commit

        # Decide whether we must (or already did) commit to pure ON_DEMAND to guarantee completion.
        if (not self._committed_to_on_demand) and (
            time_remaining <= time_needed_od + self._safety_margin
        ):
            self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            # From now on, always choose ON_DEMAND; never revert to SPOT.
            return ClusterType.ON_DEMAND

        # ---- Pre-commit phase: favor SPOT when possible, otherwise possibly idle or switch region. ----

        # Update no-spot streak in the current region.
        if has_spot:
            self._no_spot_time_in_region = 0.0
        else:
            self._no_spot_time_in_region += self._gap

        # Optional multi-region exploration: if spot has been unavailable for a long time,
        # try another region (cyclically).
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 1

        if (not has_spot) and num_regions > 1:
            if (
                self._no_spot_time_in_region >= self._region_switch_unavailable_threshold
                and (time_elapsed - self._last_region_switch_time)
                >= self._region_switch_cooldown
            ):
                current_region = int(self.env.get_current_region())
                next_region = (current_region + 1) % num_regions
                if next_region != current_region:
                    self.env.switch_region(next_region)
                    self._last_region_switch_time = time_elapsed
                    self._no_spot_time_in_region = 0.0

        # If spot is available in (current) region, always use it in pre-commit phase.
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable: decide between idling (NONE) and switching to ON_DEMAND.
        # Compute how much extra slack we currently have beyond what's needed for a
        # guaranteed ON_DEMAND-only completion.
        slack_excess = time_remaining - (time_needed_od + self._safety_margin)

        if slack_excess > self._none_slack_threshold:
            # We still have plenty of extra slack; waiting costs nothing but time,
            # may allow us to exploit spot later cheaply.
            return ClusterType.NONE

        # Slack is getting tight: switch to ON_DEMAND now and commit permanently.
        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND