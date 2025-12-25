import json
from argparse import Namespace
from typing import Optional, List

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

        # Strategy state
        self._initialized = False
        self._od_lock = False  # Once True, we stick to on-demand to guarantee completion
        self._alpha_prior = 1.0
        self._beta_prior = 1.0
        self._obs_counts: Optional[List[int]] = None
        self._up_counts: Optional[List[int]] = None
        self._last_region: Optional[int] = None

        return self

    def _init_once(self):
        if self._initialized:
            return
        n = self.env.get_num_regions()
        self._obs_counts = [0] * n
        self._up_counts = [0] * n
        self._last_region = self.env.get_current_region()
        self._initialized = True

    def _best_region(self, current_region: int) -> int:
        # Choose region with highest smoothed availability estimate
        # score = (up + alpha) / (obs + alpha + beta)
        best_idx = current_region
        best_score = -1.0
        for i in range(self.env.get_num_regions()):
            obs = self._obs_counts[i]
            up = self._up_counts[i]
            score = (up + self._alpha_prior) / (obs + self._alpha_prior + self._beta_prior)
            # Prefer current region slightly to avoid unnecessary switching oscillations
            if i == current_region:
                score += 1e-6
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time)
        remaining = max(0.0, self.task_duration - done)
        return remaining

    def _should_commit_to_od(self, time_left: float, remaining_work: float, gap: float) -> bool:
        # Conservative commit threshold:
        # We need remaining_work plus one restart overhead to start OD now.
        # Add half gap as discretization buffer.
        needed = remaining_work + self.restart_overhead + 0.5 * gap
        return time_left <= needed

    def _can_wait_one_step(self, time_left: float, remaining_work: float, gap: float) -> bool:
        # After waiting one full step (gap), will we still have enough time to finish
        # by switching to OD then?
        needed_next = remaining_work + self.restart_overhead + 0.5 * gap
        return (time_left - gap) > needed_next

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        gap = self.env.gap_seconds
        cur_region = self.env.get_current_region()
        # Update observation statistics for the current region
        self._obs_counts[cur_region] += 1
        if has_spot:
            self._up_counts[cur_region] += 1

        # Compute remaining work and time left
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            # Completed; no need to run further
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Past deadline; best effort (shouldn't happen in ideal flow)
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # If we've already committed to OD to guarantee completion, stick with it
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Decide if it's time to commit to OD now
        if self._should_commit_to_od(time_left, remaining_work, gap):
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # If Spot is available now, prefer Spot
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable now.
        # Decide to wait or to switch to OD based on slack.
        if self._can_wait_one_step(time_left, remaining_work, gap):
            # We can afford to wait; switch to the best region to improve next-step odds.
            best_region = self._best_region(cur_region)
            if best_region != cur_region:
                self.env.switch_region(best_region)
            return ClusterType.NONE

        # Not safe to wait; commit to OD to ensure on-time completion.
        self._od_lock = True
        return ClusterType.ON_DEMAND
