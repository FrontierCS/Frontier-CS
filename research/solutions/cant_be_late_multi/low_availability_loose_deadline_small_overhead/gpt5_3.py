import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbt_guardrail_rr"

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

        # Internal state for strategy
        self._commit_to_od = False
        self._unavail_streak = 0
        self._last_switch_step = -10**9
        self._region_switch_threshold_seconds = 1800.0  # switch region after 30 min of no spot
        self._use_region_switching = True
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize/maintain commitment to on-demand if already running it
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True

        # Compute basic timing
        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        done = float(sum(self.task_done_time))
        remaining = max(0.0, float(self.task_duration) - done)
        time_left = max(0.0, float(self.deadline) - elapsed)

        # If the task seems completed, choose NONE
        if remaining <= 0.0:
            return ClusterType.NONE

        # If already committed to on-demand, keep running on-demand
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Latest fallback check: ensure time to switch to OD and finish within deadline
        # Need restart_overhead once to switch to OD and remaining work time.
        slack_now = time_left - (remaining + float(self.restart_overhead))

        # If no slack to keep gambling on spot, immediately commit to on-demand
        if slack_now <= 0.0:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # If spot is available this step, use it
        if has_spot:
            self._unavail_streak = 0
            return ClusterType.SPOT

        # Spot not available: consider waiting (NONE) if still safe for one step
        # After waiting one step (no progress), we must still be able to finish on OD.
        if time_left - gap >= (remaining + float(self.restart_overhead)):
            # We can wait safely this step
            self._unavail_streak += 1

            # Optional multi-region exploration while waiting
            if self._use_region_switching:
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    step_index = int(math.floor(elapsed / max(1e-9, gap)))
                    threshold_steps = max(1, int(round(self._region_switch_threshold_seconds / max(1e-9, gap))))
                    if self._unavail_streak >= threshold_steps and (step_index - self._last_switch_step) >= 1:
                        new_region = (self.env.get_current_region() + 1) % num_regions
                        self.env.switch_region(new_region)
                        self._last_switch_step = step_index
                        self._unavail_streak = 0
            return ClusterType.NONE

        # Not safe to wait; switch to on-demand now
        self._commit_to_od = True
        return ClusterType.ON_DEMAND