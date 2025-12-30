import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "dynamic_deadline_aware_v1"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and state-tracking variables.
        """
        # The number of past time steps to use for estimating spot availability.
        self.HISTORY_WINDOW_SIZE = 250
        
        # A default guess for spot availability before we have enough history.
        # Chosen based on the problem's stated range of 4-40%.
        self.INITIAL_SPOT_PROBABILITY = 0.22
        
        # A floor for the probability estimate to prevent division by zero.
        self.MIN_SPOT_PROBABILITY = 0.01
        
        # A safety multiplier for the "wait vs pay" decision to account for the
        # high variance of waiting for a probabilistic event.
        self.WAIT_COST_SAFETY_FACTOR = 1.5

        # A deque to efficiently manage the sliding window of spot history.
        self.spot_availability_history = collections.deque(maxlen=self.HISTORY_WINDOW_SIZE)
        
        # Caching for work_done calculation to avoid re-summing a long list every step.
        self._work_done_cache = 0.0
        self._last_task_done_len = 0
        
        return self

    def _update_work_done(self) -> float:
        """
        Calculates the total work completed so far.
        Uses a cache to avoid re-calculating the sum over the entire history.
        """
        if len(self.task_done_time) > self._last_task_done_len:
            new_segments = self.task_done_time[self._last_task_done_len:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._last_task_done_len = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        current_time = self.env.elapsed_seconds
        self.spot_availability_history.append(1 if has_spot else 0)

        work_done = self._update_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        point_of_no_return = self.deadline - work_remaining
        if current_time >= point_of_no_return:
            return ClusterType.ON_DEMAND

        time_remaining_to_deadline = self.deadline - current_time
        current_slack = time_remaining_to_deadline - work_remaining

        if has_spot:
            slack_needed_for_preemption = self.restart_overhead + self.env.gap_seconds
            
            if current_slack < slack_needed_for_preemption:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT
        else:
            if len(self.spot_availability_history) < 10:
                p_spot = self.INITIAL_SPOT_PROBABILITY
            else:
                p_spot = sum(self.spot_availability_history) / len(self.spot_availability_history)
            
            p_spot = max(p_spot, self.MIN_SPOT_PROBABILITY)

            expected_slack_cost_of_waiting = self.env.gap_seconds * ((1.0 / p_spot) - 1.0)
            
            if current_slack > expected_slack_cost_of_waiting * self.WAIT_COST_SAFETY_FACTOR:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)