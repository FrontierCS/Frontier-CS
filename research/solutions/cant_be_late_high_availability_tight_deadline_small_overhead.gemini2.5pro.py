import math
from argparse import ArgumentParser

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self._num_spot_attempts: int = 0
        self._num_preemptions: int = 0
        self._last_work_done: float = 0.0

        # Hyperparameters for the adaptive logic
        # Based on stated spot unavailability of 22-57%
        self._initial_pessimistic_preemption_rate: float = 0.4
        # Number of samples before trusting the observed rate
        self._min_samples_for_history: int = 20
        # A cap to prevent extreme rates from single unlucky events
        self._preemption_rate_cap: float = 0.70
        # A threshold to consider spot as completely unusable
        self._unusable_spot_rate_threshold: float = 0.99

        # Caching total work done to avoid re-computing the sum at every step
        self._cached_work_done: float = 0.0
        self._cached_work_done_timestamp: float = -1.0
        
        return self

    def _get_work_done(self) -> float:
        if self.env.elapsed_seconds == self._cached_work_done_timestamp:
            return self._cached_work_done
        
        work_done = sum(end - start for start, end in self.task_done_time)
        self._cached_work_done = work_done
        self._cached_work_done_timestamp = self.env.elapsed_seconds
        return work_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_work_done = self._get_work_done()

        if last_cluster_type == ClusterType.SPOT and current_work_done == self._last_work_done:
             self._num_preemptions += 1
        
        work_remaining = self.task_duration - current_work_done

        if work_remaining <= 1e-6:
            self._last_work_done = current_work_done
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        slack = time_to_deadline - work_remaining

        if self._num_spot_attempts > self._min_samples_for_history:
            preemption_rate = self._num_preemptions / (self._num_spot_attempts + 1e-9)
        else:
            preemption_rate = self._initial_pessimistic_preemption_rate
            
        effective_preemption_rate = min(preemption_rate, self._preemption_rate_cap)

        buffer = 0.0
        if effective_preemption_rate < self._unusable_spot_rate_threshold:
            if self.env.gap_seconds > 0:
                steps_remaining = work_remaining / self.env.gap_seconds
                # Expected number of failures for N successes with failure prob p: N * (p / (1-p))
                expected_failures = steps_remaining * (effective_preemption_rate / (1.0 - effective_preemption_rate))
                buffer = expected_failures * self.restart_overhead
        else:
            buffer = float('inf')

        chosen_type = ClusterType.ON_DEMAND
        if slack > buffer:
            if has_spot:
                chosen_type = ClusterType.SPOT
            else:
                chosen_type = ClusterType.ON_DEMAND
        else:
            chosen_type = ClusterType.ON_DEMAND

        if chosen_type == ClusterType.SPOT:
            self._num_spot_attempts += 1
        
        self._last_work_done = current_work_done
        return chosen_type

    @classmethod
    def _from_args(cls, parser: ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)