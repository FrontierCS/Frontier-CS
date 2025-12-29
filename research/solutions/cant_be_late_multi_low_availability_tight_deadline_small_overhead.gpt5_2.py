import json
import random
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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

        # Initialize internal state
        self.commit_od = False
        self._rng = random.Random(1337)
        try:
            self.num_regions = int(self.env.get_num_regions())
        except Exception:
            self.num_regions = 1

        self.region_scores: List[float] = [0.5 for _ in range(self.num_regions)]
        self.region_visits: List[int] = [0 for _ in range(self.num_regions)]
        self.last_has_spot_by_region: List[int] = [0 for _ in range(self.num_regions)]
        self.round_robin_idx = 0
        self.alpha = 0.1  # EMA update rate for region scores
        self.explore_prob = 0.05  # small exploration chance among regions
        self.stick_region_when_spot = True  # avoid switching when spot available
        # Safety slack cushion when deciding to risk a spot step
        self.min_spot_cushion_steps = 1

        return self

    def _sum_done(self) -> float:
        return float(sum(self.task_done_time)) if hasattr(self, "task_done_time") else 0.0

    def _time_left(self) -> float:
        return float(self.deadline - self.env.elapsed_seconds)

    def _remaining_work(self) -> float:
        return max(0.0, float(self.task_duration - self._sum_done()))

    def _overhead_to_start_od(self, last_cluster_type: ClusterType) -> float:
        # Starting or switching to ON_DEMAND incurs restart_overhead, unless already on ON_DEMAND
        return 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

    def _enough_cushion_for_one_more_spot_step(self, time_left: float, remaining_work: float) -> bool:
        # Ensure that even if we waste up to min_spot_cushion_steps steps (each of gap_seconds),
        # we can still switch to OD and finish with restart_overhead + remaining_work.
        cushion_seconds = self.env.gap_seconds * self.min_spot_cushion_steps
        return (time_left - cushion_seconds) > (self.restart_overhead + remaining_work)

    def _maybe_switch_region_on_wait(self, has_spot: bool) -> None:
        # Update score for current region based on observation
        cur_r = self.env.get_current_region()
        observed = 1.0 if has_spot else 0.0
        # EMA update
        self.region_scores[cur_r] = (1.0 - self.alpha) * self.region_scores[cur_r] + self.alpha * observed
        self.region_visits[cur_r] += 1
        self.last_has_spot_by_region[cur_r] = int(observed)

        # Choose next region when we plan to wait (NONE). Prefer regions with higher score.
        # Occasionally explore randomly.
        if self.num_regions <= 1:
            return

        if self._rng.random() < self.explore_prob:
            # Explore random region different from current
            candidates = [i for i in range(self.num_regions) if i != cur_r]
            if candidates:
                nxt = self._rng.choice(candidates)
                if nxt != cur_r:
                    self.env.switch_region(nxt)
            return

        # Otherwise pick the best-scoring region (ties broken by round-robin order)
        best_score = -1.0
        best_idx = cur_r
        # To avoid getting stuck, start scan from a rotating pointer
        start = self.round_robin_idx % self.num_regions
        for k in range(self.num_regions):
            idx = (start + k) % self.num_regions
            # Prefer regions different from current when current has no spot
            if idx == cur_r and has_spot is False:
                continue
            score = self.region_scores[idx]
            if score > best_score or (score == best_score and self.region_visits[idx] < self.region_visits[best_idx]):
                best_score = score
                best_idx = idx
        self.round_robin_idx = (self.round_robin_idx + 1) % self.num_regions
        if best_idx != cur_r:
            self.env.switch_region(best_idx)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, stick to it to avoid unnecessary overhead and risk.
        if self.commit_od:
            return ClusterType.ON_DEMAND

        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self._time_left()
        gap = float(self.env.gap_seconds)
        overhead_to_start_od = self._overhead_to_start_od(last_cluster_type)

        # If we must switch to OD now to guarantee completion, do so and commit.
        # Condition: time_left <= overhead_to_start_od + remaining_work
        if time_left <= overhead_to_start_od + remaining_work:
            self.commit_od = True
            return ClusterType.ON_DEMAND

        # If we have enough cushion to risk another step on spot (even if wasted)
        risk_spot_now = self._enough_cushion_for_one_more_spot_step(time_left, remaining_work)

        # If spot is available and we can risk, use spot.
        if has_spot and risk_spot_now:
            # Optionally avoid unnecessary region switching when spot is available
            return ClusterType.SPOT

        # If we cannot risk another spot step (cushion too small), go OD now.
        if not risk_spot_now:
            self.commit_od = True
            return ClusterType.ON_DEMAND

        # We still have cushion but spot is not available now.
        # Wait (NONE) and try to reposition to a better region for next step.
        self._maybe_switch_region_on_wait(has_spot)
        return ClusterType.NONE