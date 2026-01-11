import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        # Lazy init of runtime state
        self._inited = False
        return self

    def _lazy_init(self):
        if self._inited:
            return
        # Running sums for efficiency
        self._done_sum = 0.0
        self._done_len = 0
        # Commit to OD flag
        self._od_committed = False
        # Region tracking
        self._num_regions = self.env.get_num_regions()
        if self._num_regions <= 0:
            self._num_regions = 1
        self._region_scores = [0.5 for _ in range(self._num_regions)]
        self._ema_decay = 0.95  # for spot availability scoring per region
        self._last_region_idx = self.env.get_current_region()
        # Margins
        gap = float(self.env.gap_seconds)
        # Commit margin should be at least one step to avoid overshoot, capped by overhead somewhat
        self._commit_margin = max(gap, min(self.restart_overhead * 0.75, 900.0))
        # Require extra slack to attempt launching SPOT from a non-SPOT state
        self._start_spot_extra_slack = self.restart_overhead + self._commit_margin
        self._inited = True

    def _update_done_sum(self):
        if self._done_len < len(self.task_done_time):
            # Incremental update of completed work
            new_sum = sum(self.task_done_time[self._done_len :])
            self._done_sum += new_sum
            self._done_len = len(self.task_done_time)

    def _update_region_score(self, has_spot: bool):
        # Update exponential moving average score for current region
        r = self.env.get_current_region()
        if 0 <= r < self._num_regions:
            decay = self._ema_decay
            cur = self._region_scores[r]
            obs = 1.0 if has_spot else 0.0
            self._region_scores[r] = cur * decay + obs * (1.0 - decay)

    def _best_region(self, exclude_idx: int):
        # Pick region with highest score (excluding current)
        best_idx = None
        best_score = -1.0
        for i in range(self._num_regions):
            if i == exclude_idx:
                continue
            s = self._region_scores[i]
            if s > best_score:
                best_score = s
                best_idx = i
        # Fall back to next region in round-robin if all equal or None
        if best_idx is None:
            if self._num_regions > 1:
                best_idx = (exclude_idx + 1) % self._num_regions
            else:
                best_idx = exclude_idx
        return best_idx

    def _compute_slack_to_od(self, last_cluster_type: ClusterType, t_remaining: float, w_remaining: float) -> float:
        # Slack if we switch to OD now and run until completion
        od_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return t_remaining - (w_remaining + od_overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()
        self._update_region_score(has_spot)

        # If already done, no need to run
        w_remaining = max(self.task_duration - self._done_sum, 0.0)
        if w_remaining <= 0.0:
            return ClusterType.NONE

        t_remaining = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If we've committed to OD, stay on OD until done
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # If currently on SPOT and SPOT is available, continue using SPOT to avoid overhead.
        if last_cluster_type == ClusterType.SPOT and has_spot:
            return ClusterType.SPOT

        # Compute current slack to OD
        slack_to_od = self._compute_slack_to_od(last_cluster_type, t_remaining, w_remaining)

        # If slack is tight, commit to OD to guarantee completion.
        if slack_to_od <= self._commit_margin:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Not committed yet and we have some slack
        if has_spot:
            # Starting SPOT from a non-SPOT state incurs overhead; ensure we have extra slack.
            if slack_to_od > self._start_spot_extra_slack:
                return ClusterType.SPOT
            else:
                # Prefer to commit to OD rather than risk insufficient slack after additional overhead.
                self._od_committed = True
                return ClusterType.ON_DEMAND

        # Spot not available here; wait (NONE) and try better region if any.
        # Switch to the best region by score to hunt for spot next step.
        current_region = self.env.get_current_region()
        best_region = self._best_region(current_region)
        if best_region is not None and best_region != current_region:
            self.env.switch_region(best_region)
        return ClusterType.NONE