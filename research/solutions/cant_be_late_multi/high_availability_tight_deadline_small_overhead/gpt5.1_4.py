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

        # Strategy state (initialized here, refined in first _step)
        self._online_initialized = False

        # Cached task progress
        self._task_done_sum = 0.0
        self._task_done_len = 0

        # Mode flags
        self.force_on_demand = False

        # Region statistics (lazy init)
        self.num_regions = None
        self.region_steps = None
        self.region_spot_available = None

        # Region selection hyper-parameters
        self.region_prior_a = 1.0
        self.region_prior_b = 1.0
        self.switch_delta_threshold = 0.15
        self.switch_cooldown_steps = 20
        self.last_switch_step = -1000000
        self.total_steps = 0

        # Time-based thresholds (lazy, depend on env)
        self.gap_seconds = None
        self.commit_margin = None
        self.wait_none_threshold = None

        return self

    def _online_init(self) -> None:
        """Initialize state that depends on the environment."""
        if self._online_initialized:
            return
        self._online_initialized = True

        # Environment-dependent values
        self.gap_seconds = float(self.env.gap_seconds)
        # restart_overhead and others are provided in seconds by base class
        overhead = float(self.restart_overhead)

        # Number of regions and per-region stats
        self.num_regions = int(self.env.get_num_regions())
        self.region_steps = [0] * self.num_regions
        self.region_spot_available = [0] * self.num_regions

        # Safety margin: how much slack (in seconds) we require before
        # permanently switching to ON_DEMAND.
        # Chosen relative to step size and restart overhead.
        self.commit_margin = 4.0 * (self.gap_seconds + overhead)

        # Threshold above which we are comfortable idling (NONE) when spot is
        # unavailable.
        self.wait_none_threshold = self.commit_margin + 3.0 * self.gap_seconds

    def _update_task_done_cache(self) -> float:
        """Incrementally maintain sum(self.task_done_time)."""
        cur_len = len(self.task_done_time)
        if cur_len > self._task_done_len:
            # Add only new segments
            s = 0.0
            for i in range(self._task_done_len, cur_len):
                s += self.task_done_time[i]
            self._task_done_sum += s
            self._task_done_len = cur_len
        return self._task_done_sum

    def _best_region_index(self) -> int:
        """Return index of region with highest estimated spot availability."""
        alpha = self.region_prior_a
        beta = self.region_prior_b
        best_idx = 0
        best_score = -1.0
        for r in range(self.num_regions):
            steps_r = self.region_steps[r]
            spot_r = self.region_spot_available[r]
            score = (spot_r + alpha) / (steps_r + alpha + beta)
            if score > best_score:
                best_score = score
                best_idx = r
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization that depends on env
        self._online_init()

        self.total_steps += 1

        # Update region stats for current observation
        current_region = self.env.get_current_region()
        if self.region_steps is not None:
            self.region_steps[current_region] += 1
            if has_spot:
                self.region_spot_available[current_region] += 1

        # Update cached work done
        work_done = self._update_task_done_cache()
        remaining_work = max(0.0, float(self.task_duration) - work_done)

        # If work finished, do nothing further
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time accounting
        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed

        # Effective remaining restart overhead: be conservative and use max of
        # configured overhead and any pending overhead.
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))
        effective_overhead = max(float(self.restart_overhead), pending_overhead)

        # Slack: time we can afford to "waste" beyond the pure ON_DEMAND plan
        slack = time_left - (remaining_work + effective_overhead)

        # Once we decide to force ON_DEMAND, never go back to SPOT/NONE
        if self.force_on_demand or slack <= self.commit_margin:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Before we hit the ON_DEMAND-only region, we try to exploit SPOT.
        if has_spot:
            # Spot available: always take it while we have sufficient slack.
            return ClusterType.SPOT

        # Spot not available in current region and we are not yet forcing ON_DEMAND.
        # Consider switching to a better region for future steps.
        if (
            self.total_steps - self.last_switch_step >= self.switch_cooldown_steps
            and self.num_regions is not None
            and self.num_regions > 1
        ):
            best_region = self._best_region_index()
            if best_region != current_region:
                alpha = self.region_prior_a
                beta = self.region_prior_b
                cur_steps = self.region_steps[current_region]
                cur_spot = self.region_spot_available[current_region]
                cur_score = (cur_spot + alpha) / (cur_steps + alpha + beta)

                best_steps = self.region_steps[best_region]
                best_spot = self.region_spot_available[best_region]
                best_score = (best_spot + alpha) / (best_steps + alpha + beta)

                if best_score - cur_score >= self.switch_delta_threshold:
                    self.env.switch_region(best_region)
                    self.last_switch_step = self.total_steps

        # Decide between idling (NONE) and paying for ON_DEMAND while spot is down.
        if slack >= self.wait_none_threshold:
            # Plenty of slack left: we can afford to wait for spot to return.
            return ClusterType.NONE
        else:
            # Slack is moderate: fall back to ON_DEMAND while spot is unavailable.
            return ClusterType.ON_DEMAND