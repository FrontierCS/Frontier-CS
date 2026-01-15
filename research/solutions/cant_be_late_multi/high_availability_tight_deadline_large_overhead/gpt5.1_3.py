import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        self._setup_policy()
        return self

    def _setup_policy(self) -> None:
        # Tracking for completed work
        self._prev_segments_len = len(getattr(self, "task_done_time", []))
        if self._prev_segments_len > 0:
            self._total_done = float(sum(self.task_done_time))
        else:
            self._total_done = 0.0
        self._last_total_done = self._total_done

        # Time tracking
        self._last_elapsed_seconds = getattr(self.env, "elapsed_seconds", 0.0)

        # Cluster-type performance stats (not heavily used, but kept for extensibility)
        self._spot_time = 0.0
        self._spot_work = 0.0
        self._od_time = 0.0
        self._od_work = 0.0

        # Step counters / availability stats
        self._total_steps = 0
        self._spot_avail_steps = 0
        self._spot_not_avail_steps = 0

        # Commitment flag: once set, always use on-demand
        self._commit_to_on_demand = False

        # Core parameters
        self.task_duration = float(getattr(self, "task_duration", 0.0))
        self.deadline = float(getattr(self, "deadline", 0.0))
        self.restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 1.0))

        # Initial slack: total time beyond required pure running time
        initial_slack = self.deadline - self.task_duration
        if initial_slack < 0.0:
            initial_slack = 0.0
        self._initial_slack = initial_slack

        # Commit-to-on-demand slack threshold.
        # Chosen to be big enough to safely absorb one restart overhead and a time step,
        # but small compared to total slack where applicable.
        base_commit = gap + 2.0 * self.restart_overhead
        if initial_slack > 0.0:
            half_slack = 0.5 * initial_slack
            commit_slack_threshold = base_commit if base_commit < half_slack else half_slack
            if commit_slack_threshold < 0.0:
                commit_slack_threshold = 0.0
        else:
            commit_slack_threshold = 0.0
        self._commit_slack_threshold = commit_slack_threshold

        # Threshold where we start using on-demand when spot is unavailable.
        # We allow a large portion of initial slack to be spent on waiting / spot overhead,
        # but keep a buffer above the commit threshold.
        idle_fraction = 0.3  # fraction of (initial_slack - commit_slack_threshold) we keep as buffer
        if initial_slack > commit_slack_threshold:
            extra_slack = initial_slack - commit_slack_threshold
            use_od_no_spot_threshold = commit_slack_threshold + extra_slack * idle_fraction
        else:
            use_od_no_spot_threshold = commit_slack_threshold
        self._use_od_no_spot_threshold = use_od_no_spot_threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Defensive lazy init if solve() wasn't called (shouldn't happen in judge)
        if not hasattr(self, "_prev_segments_len"):
            self._setup_policy()

        now = self.env.elapsed_seconds

        # Update completed work based on task_done_time segments
        cur_len = len(self.task_done_time)
        if cur_len > self._prev_segments_len:
            added = 0.0
            segments = self.task_done_time
            for i in range(self._prev_segments_len, cur_len):
                added += segments[i]
            self._total_done += added
            self._prev_segments_len = cur_len

        # Update per-cluster statistics
        delta_time = now - self._last_elapsed_seconds
        if delta_time < 0.0:
            delta_time = 0.0
        new_work = self._total_done - self._last_total_done
        if new_work < 0.0:
            new_work = 0.0

        if last_cluster_type == ClusterType.SPOT:
            self._spot_time += delta_time
            self._spot_work += new_work
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self._od_time += delta_time
            self._od_work += new_work

        self._last_elapsed_seconds = now
        self._last_total_done = self._total_done

        # Availability statistics
        self._total_steps += 1
        if has_spot:
            self._spot_avail_steps += 1
        else:
            self._spot_not_avail_steps += 1

        # Remaining work and time
        remaining_work = self.task_duration - self._total_done
        if remaining_work <= 0.0:
            # Task already finished; don't pay extra cost
            return ClusterType.NONE

        time_left = self.deadline - now
        if time_left <= 0.0:
            # Past deadline: no action can fix it, avoid further cost
            return ClusterType.NONE

        slack = time_left - remaining_work

        # Decide if we must commit to on-demand
        if not self._commit_to_on_demand:
            if (
                slack <= self._commit_slack_threshold
                or time_left <= self._commit_slack_threshold
                or time_left <= remaining_work + self.restart_overhead
            ):
                self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit behavior: prefer Spot when available, otherwise potentially wait
        if has_spot:
            # Spot available: cheapest option, use it
            return ClusterType.SPOT
        else:
            # Spot unavailable: if we still have comfortable slack, wait; otherwise use on-demand
            if slack > self._use_od_no_spot_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND