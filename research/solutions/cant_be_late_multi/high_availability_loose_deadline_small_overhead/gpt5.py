import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbm_guarded_spot_strategy_v1"

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

        # Internal state for efficiency and strategy control
        self._work_done_sum = 0.0
        self._last_segments_len = 0

        self._num_regions = self.env.get_num_regions()
        self._current_region = self.env.get_current_region()

        # Decision state
        self._commit_to_ondemand = False

        # Spot unavailability tracking for optional region switching while waiting
        self._unavail_streak_steps = 0
        self._last_switch_elapsed = -1e18  # second
        # Region switching parameters (conservative)
        self._switch_wait_seconds = 300.0  # wait at least 5 minutes of continuous unavailability before switching
        self._switch_cooldown_seconds = 300.0  # throttle switching to avoid thrashing

        # Safety buffer for committing to on-demand to hedge against a late preemption
        # Use 2 * overhead + small fudge to tolerate one preemption before switching.
        H = self.restart_overhead
        step = self.env.gap_seconds
        self._commit_buffer_seconds = (2.0 * H) + max(60.0, 2.0 * step)

        return self

    def _update_progress_sum(self):
        # Incremental sum of task_done_time to avoid O(n) each step
        l = len(self.task_done_time)
        if l != self._last_segments_len:
            # Sum only the new entries
            total_add = 0.0
            for i in range(self._last_segments_len, l):
                total_add += self.task_done_time[i]
            self._work_done_sum += total_add
            self._last_segments_len = l
        return self._work_done_sum

    def _should_commit_to_on_demand(self, remaining_work: float, time_left: float) -> bool:
        # If time left is less than or close to the time required on On-Demand (plus safety), commit.
        # We account for potential overhead when switching and an extra safety buffer.
        commit_threshold = remaining_work + self.restart_overhead + self._commit_buffer_seconds
        return time_left <= commit_threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to On-Demand, keep using it until finish.
        if self._commit_to_ondemand:
            return ClusterType.ON_DEMAND

        # Efficiently compute progress and remaining work/time
        progress = self._update_progress_sum()
        remaining_work = max(0.0, self.task_duration - progress)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)

        # If we are running out of time, commit to On-Demand now
        if self._should_commit_to_on_demand(remaining_work, time_left):
            self._commit_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available
        if has_spot:
            # Reset unavailability streak since spot is present
            self._unavail_streak_steps = 0
            return ClusterType.SPOT

        # Spot not available in current region
        # Consider switching region cautiously while waiting (choose NONE to avoid errors)
        self._unavail_streak_steps += 1

        # If getting closer to the deadline due to waiting, escalate to On-Demand
        # We check again conservatively with a small lookahead for the next step.
        # If at next step we might not have enough time, switch to On-Demand now.
        H = self.restart_overhead
        step = self.env.gap_seconds
        lookahead_threshold = remaining_work + H + self._commit_buffer_seconds
        if time_left <= lookahead_threshold + step:
            self._commit_to_ondemand = True
            return ClusterType.ON_DEMAND

        # Optional region switch when waiting to leverage multi-region diversity
        if self._num_regions > 1:
            waited_seconds = self._unavail_streak_steps * step
            time_since_last_switch = self.env.elapsed_seconds - self._last_switch_elapsed
            if waited_seconds >= self._switch_wait_seconds and time_since_last_switch >= self._switch_cooldown_seconds:
                # Round-robin to next region
                next_region = (self.env.get_current_region() + 1) % self._num_regions
                if next_region != self.env.get_current_region():
                    self.env.switch_region(next_region)
                    self._last_switch_elapsed = self.env.elapsed_seconds
                    # Reset streak after switching to avoid rapid subsequent switches
                    self._unavail_streak_steps = 0

        # Still early enough: wait for Spot to return to minimize cost
        return ClusterType.NONE