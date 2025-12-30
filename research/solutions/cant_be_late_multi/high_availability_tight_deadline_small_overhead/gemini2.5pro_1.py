import json
from argparse import Namespace
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_explorer"

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

        self.is_initialized = False
        return self

    def _initialize_state(self):
        self.num_regions = self.env.get_num_regions()
        
        self.history_window_size = 20
        self.initial_spot_proba = 0.9
        self.explore_slack_factor = 2.0
        self.explore_proba_threshold = 0.75
        self.panic_mode_safety_factor = 1.05

        self.spot_history = [
            deque(maxlen=self.history_window_size) for _ in range(self.num_regions)
        ]
        self.probas = [self.initial_spot_proba] * self.num_regions
        self.state = 'STABLE'
        
        self.is_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.is_initialized:
            self._initialize_state()
        
        self._update_knowledge(has_spot)

        work_remaining = self.task_duration - sum(self.task_done_time)
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - self.env.elapsed_seconds
        panic_threshold = work_remaining + self.restart_overhead * self.panic_mode_safety_factor
        if time_remaining <= panic_threshold:
            self.state = 'STABLE'
            return ClusterType.ON_DEMAND
        
        if self.state == 'STABLE':
            return self._decide_from_stable_state(has_spot, work_remaining, time_remaining)
        
        elif self.state == 'EXPLORING':
            return self._decide_from_exploring_state(has_spot)
        
        return ClusterType.ON_DEMAND

    def _update_knowledge(self, has_spot: bool):
        current_region = self.env.get_current_region()
        self.spot_history[current_region].append(1 if has_spot else 0)
        history = self.spot_history[current_region]
        if len(history) > 0:
            self.probas[current_region] = sum(history) / len(history)

    def _decide_from_stable_state(self, has_spot, work_remaining, time_remaining):
        if has_spot:
            return ClusterType.SPOT
        else:
            if self._should_explore(work_remaining, time_remaining):
                self._switch_to_best_alt_region()
                self.state = 'EXPLORING'
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    def _decide_from_exploring_state(self, has_spot: bool):
        self.state = 'STABLE'
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    def _should_explore(self, work_remaining, time_remaining) -> bool:
        slack = time_remaining - work_remaining
        if slack < self.restart_overhead * self.explore_slack_factor:
            return False

        best_alt_proba, _ = self._get_best_alt_region()
        
        if best_alt_proba is None:
            return False

        if best_alt_proba > self.explore_proba_threshold:
            return True
        
        return False

    def _get_best_alt_region(self):
        current_region = self.env.get_current_region()
        candidate_regions = []
        for i in range(self.num_regions):
            if i != current_region:
                candidate_regions.append((self.probas[i], i))
        
        if not candidate_regions:
            return None, None
        
        return max(candidate_regions)

    def _switch_to_best_alt_region(self):
        _, best_alt_region = self._get_best_alt_region()
        if best_alt_region is not None:
            self.env.switch_region(best_alt_region)