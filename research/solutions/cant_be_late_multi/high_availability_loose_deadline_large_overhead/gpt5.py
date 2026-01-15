import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_v8"

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

        # Internal state for efficient progress tracking
        self._work_done_total = 0.0
        self._last_task_len = 0  # number of entries already accounted from task_done_time
        self._last_step_progress = 0.0

        # Decision flags and thresholds
        self._commit_to_od = False  # Once True, we keep using On-Demand until finish
        self._safety_padding = 1.0  # seconds padding for numeric safety

        # Region management
        num_regions = self.env.get_num_regions()
        self._gap = self.env.gap_seconds
        self._last_region_switch_elapsed = -1e18
        self._switch_cooldown_seconds = 4 * 3600.0  # avoid frequent switching (4 hours)
        self._switch_min_improvement = 0.08  # improvement threshold to consider switching
        self._preempt_progress_threshold = 0.10  # ratio to consider near-zero progress

        # Stats per region for spot performance
        self._region_stats = [
            {
                "spot_attempts": 0,
                "spot_success_sec": 0.0,
                "last_progress": 0.0,
                "bad_streak": 0,
                "good_streak": 0,
                "fail_score": 0,
            }
            for _ in range(num_regions)
        ]

        # Prior for success rate smoothing
        self._prior_attempts = 3.0
        self._prior_success_ratio = 0.97

        return self

    def _update_progress_and_stats(self, last_cluster_type: ClusterType):
        # Update cumulative work done based on new task_done_time entries only
        if len(self.task_done_time) > self._last_task_len:
            new_entries = self.task_done_time[self._last_task_len :]
            delta = 0.0
            for v in new_entries:
                delta += float(v)
            self._work_done_total += delta
            self._last_step_progress = delta
            self._last_task_len = len(self.task_done_time)
        else:
            self._last_step_progress = 0.0

        # Update per-region stats if last step used SPOT
        if last_cluster_type == ClusterType.SPOT:
            region = self.env.get_current_region()
            stats = self._region_stats[region]
            stats["spot_attempts"] += 1
            # Cap progress to be within [0, gap] for stats stability
            prog = self._last_step_progress
            if prog < 0.0:
                prog = 0.0
            elif prog > self._gap:
                prog = self._gap
            stats["spot_success_sec"] += prog
            stats["last_progress"] = prog
            ratio = prog / self._gap if self._gap > 0 else 0.0
            if ratio < self._preempt_progress_threshold:
                stats["bad_streak"] = stats.get("bad_streak", 0) + 1
                stats["fail_score"] = stats.get("fail_score", 0) + 1
                stats["good_streak"] = 0
            else:
                stats["bad_streak"] = 0
                stats["good_streak"] = stats.get("good_streak", 0) + 1

    def _predict_region_success(self, region_idx: int) -> float:
        stats = self._region_stats[region_idx]
        attempts = stats["spot_attempts"]
        success_sec = stats["spot_success_sec"]
        prior_succ_sec = self._prior_success_ratio * self._gap * self._prior_attempts
        denom = (attempts + self._prior_attempts) * self._gap
        if denom <= 0:
            base = self._prior_success_ratio
        else:
            base = (success_sec + prior_succ_sec) / denom
        penalty = 0.03 * float(stats.get("fail_score", 0))
        score = base - penalty
        if score < 0.0:
            score = 0.0
        if score > 1.0:
            score = 1.0
        return score

    def _choose_region_if_needed(self, has_spot: bool) -> None:
        # Only consider switching when we plan to use SPOT and have cooldown passed
        if not has_spot:
            return
        now = self.env.elapsed_seconds
        if now - self._last_region_switch_elapsed < self._switch_cooldown_seconds:
            return

        current = self.env.get_current_region()
        # Trigger switching only if last SPOT step had near-zero progress or consecutive failures
        current_stats = self._region_stats[current]
        recent_ratio = (
            (current_stats["last_progress"] / self._gap) if self._gap > 0 else 0.0
        )
        had_recent_zero_like = recent_ratio < self._preempt_progress_threshold
        has_bad_streak = current_stats.get("bad_streak", 0) >= 2

        if not (had_recent_zero_like or has_bad_streak):
            return

        # Compute predicted scores for all regions
        num_regions = self.env.get_num_regions()
        scores = [self._predict_region_success(r) for r in range(num_regions)]
        best_region = max(range(num_regions), key=lambda r: scores[r])
        best_score = scores[best_region]
        current_score = scores[current]

        # Switch only if there's a meaningful improvement and different region
        improvement = best_score - current_score
        if best_region != current and improvement >= self._switch_min_improvement:
            self.env.switch_region(best_region)
            self._last_region_switch_elapsed = now

    def _should_commit_to_od(self, remaining_work: float, time_remaining: float) -> bool:
        # We ensure that we do not risk missing the deadline
        # Commit to OD if there's not enough slack to afford another step of waiting/spot attempt
        # Conservative condition: if we try SPOT or wait for one gap, we must still be able to finish with OD.
        # If not, commit to OD now.
        if time_remaining <= remaining_work + self.restart_overhead + self._safety_padding:
            return True
        return False

    def _can_wait_one_step(self, remaining_work: float, time_remaining: float) -> bool:
        # Determine if we can afford to waste one step (gap) and still finish with OD afterward
        return (time_remaining - self._gap) > (remaining_work + self.restart_overhead + self._safety_padding)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal progress/accounting
        self._update_progress_and_stats(last_cluster_type)

        # If already finished, do nothing
        remaining_work = self.task_duration - self._work_done_total
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds

        # If we've committed to OD, keep using it to avoid extra overhead risk
        if self._commit_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Decide whether we must commit to OD now
        if self._should_commit_to_od(remaining_work, time_remaining):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # If no global spot availability this step, decide NONE vs OD based on slack
        if not has_spot:
            if self._can_wait_one_step(remaining_work, time_remaining):
                return ClusterType.NONE
            else:
                self._commit_to_od = True
                return ClusterType.ON_DEMAND

        # Spot is available; attempt SPOT if it's safe to afford one step
        # We already ensured above that trying SPOT is safe if we didn't commit.
        # Optionally switch to a better region if recent failure indicated issues
        self._choose_region_if_needed(has_spot=True)
        return ClusterType.SPOT