import json
import math
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

        # Internal state
        self._initialized = False
        self._commit_od = False

        self._alpha0 = 3.0
        self._beta0 = 1.0
        self._explore_c = 0.5
        self._switch_margin = 0.02
        self._sticky_bonus = 0.005

        self._done_sum = 0.0
        self._last_done_idx = 0

        return self

    def _init_region_stats(self):
        n = self.env.get_num_regions()
        self._num_regions = n
        self._successes = [0] * n
        self._trials = [0] * n

    def _update_done_sum(self):
        if self._last_done_idx < len(self.task_done_time):
            delta = 0.0
            for x in self.task_done_time[self._last_done_idx:]:
                delta += float(x)
            self._done_sum += delta
            self._last_done_idx = len(self.task_done_time)

    def _overhead_this_step_for(self, target_type: ClusterType, last_cluster_type: ClusterType) -> float:
        gap = float(self.env.gap_seconds)
        # If same cluster type, remaining_restart_overhead applies; else full restart overhead.
        if target_type == last_cluster_type:
            oh = float(self.remaining_restart_overhead) if hasattr(self, "remaining_restart_overhead") else 0.0
        else:
            oh = float(self.restart_overhead)
        if oh < 0.0:
            oh = 0.0
        if oh > gap:
            oh = gap
        return oh

    def _estimate_region_scores(self, current_region: int, has_spot: bool):
        # Compute UCB-like score for each region
        total_trials = sum(self._trials) + 1
        log_term = math.log(total_trials + 1.0)
        scores = []
        for i in range(self._num_regions):
            successes = self._successes[i]
            trials = self._trials[i]
            alpha = self._alpha0 + successes
            beta = self._beta0 + (trials - successes if trials >= successes else 0)
            p_est = alpha / (alpha + beta)
            bonus = self._explore_c * math.sqrt(log_term / (trials + 1.0))
            score = p_est + bonus
            scores.append(score)
        # Sticky bonus to current region if currently has spot; encourages not switching away when good.
        if has_spot and 0 <= current_region < self._num_regions:
            scores[current_region] += self._sticky_bonus
        return scores

    def _choose_next_region(self, current_region: int, has_spot: bool) -> int:
        scores = self._estimate_region_scores(current_region, has_spot)
        best_idx = max(range(self._num_regions), key=lambda i: scores[i])
        # Hysteresis: avoid switching unless significant improvement
        if scores[best_idx] - scores[current_region] > self._switch_margin:
            return best_idx
        return current_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._init_region_stats()
            self._initialized = True

        current_region = self.env.get_current_region()

        # Observe current region spot availability (bandit feedback)
        # We get observation regardless of what we run on now.
        if 0 <= current_region < self._num_regions:
            self._trials[current_region] += 1
            if has_spot:
                self._successes[current_region] += 1

        # Update cumulative done sum incrementally
        self._update_done_sum()

        # If already committed to on-demand, just stay on it.
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Compute slack
        gap = float(self.env.gap_seconds)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work < 0:
            remaining_work = 0.0

        # Slack relative to fallback to OD (including one restart overhead)
        slack = time_left - (remaining_work + float(self.restart_overhead))

        # Decide action
        action = None

        if has_spot:
            # Predicted progress if we use Spot this step
            overhead_spot = self._overhead_this_step_for(ClusterType.SPOT, last_cluster_type)
            p_spot = max(0.0, gap - overhead_spot)
            # Safe to take a spot step if slack >= (gap - p_spot)
            if slack >= (gap - p_spot) - 1e-9:
                action = ClusterType.SPOT
            else:
                # Not safe to take SPOT; switch to OD and commit
                self._commit_od = True
                return ClusterType.ON_DEMAND
        else:
            # No spot: decide between waiting or OD
            # Safe to wait one step if slack >= gap
            if slack >= gap - 1e-9:
                action = ClusterType.NONE
            else:
                # Must switch to OD and commit
                self._commit_od = True
                return ClusterType.ON_DEMAND

        # Reposition region for next step (avoid switching regions while using SPOT to be conservative)
        if action != ClusterType.SPOT:
            # Only reposition when not running Spot this step
            next_region = self._choose_next_region(current_region, has_spot)
            if next_region != current_region:
                self.env.switch_region(next_region)
        else:
            # Optionally reposition only when Spot is not available to avoid any potential overhead risks
            # Keep current region when using Spot
            pass

        return action