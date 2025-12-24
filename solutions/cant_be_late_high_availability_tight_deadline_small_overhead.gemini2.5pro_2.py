import collections
from argparse import ArgumentParser

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    A dynamic scheduling strategy that balances cost and completion risk.

    The core idea is to maintain a "safety buffer" of time. This buffer
    represents the amount of slack (time_to_deadline - work_remaining)
    we want to keep in reserve to handle unexpected events like spot
    preemptions or long periods of spot unavailability.

    The strategy operates in three modes:
    1. PANIC MODE: If the remaining time is less than or equal to the
       remaining work, there is no slack left. We must use on-demand
       instances to guarantee progress and avoid missing the deadline.

    2. DANGER ZONE: If the current slack falls below our desired safety
       buffer, we switch to on-demand. This is a proactive measure to
       make guaranteed progress and rebuild our time buffer before we
       enter panic mode. The buffer size is dynamic, scaling with the
       amount of work remaining.

    3. ECONOMY MODE: If we have sufficient slack (more than the safety
       buffer), we prioritize cost savings.
       - If a spot instance is available, we use it.
       - If spot is not available, we decide whether to wait (NONE) or use
         on-demand. This decision is based on the recently observed
         availability of spot instances. If availability has been high, we
         wait, betting that a cheap instance will soon be available. If
         availability has been poor, waiting is too risky, so we use an
         on-demand instance to make progress while preserving our time buffer.
    """
    NAME = "my_solution"

    @classmethod
    def _from_args(cls, parser: ArgumentParser):
        """
        Defines command-line arguments for tuning the strategy's parameters.
        """
        parser.add_argument('--buffer-factor', type=float, default=0.05,
                            help='Dynamic buffer size as a fraction of remaining work.')
        parser.add_argument('--min-buffer-preemptions', type=float, default=3.0,
                            help='Minimum buffer size in units of restart_overhead.')
        parser.add_argument('--history-window', type=int, default=120,
                            help='Number of past steps to estimate spot availability.')
        parser.add_argument('--min-spot-chance', type=float, default=0.40,
                            help='Minimum estimated spot availability to justify waiting.')
        args, _ = parser.parse_known_args()
        return cls(args)

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self.spot_history = None
        self.buffer_factor = None
        self.min_buffer = None
        self.history_window = None
        self.min_spot_chance_to_wait = None

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters based on arguments and
        environment values like restart_overhead.
        """
        self.buffer_factor = self.args.buffer_factor
        self.min_buffer = self.args.min_buffer_preemptions * self.restart_overhead
        self.history_window = self.args.history_window
        self.min_spot_chance_to_wait = self.args.min_spot_chance
        self.spot_history = collections.deque(maxlen=self.history_window)
        return self

    def _get_work_remaining(self) -> float:
        """Helper to calculate the remaining compute time needed."""
        return self.task_duration - sum(self.task_done_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        # 1. Update state with the latest spot availability info.
        self.spot_history.append(1 if has_spot else 0)
        work_remaining = self._get_work_remaining()

        # 2. If the job is finished, do nothing.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # 3. Calculate key metrics for decision-making.
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 4. PANIC MODE: Absolute necessity to run on-demand.
        # If remaining time is less than remaining work, we have no choice.
        if time_to_deadline <= work_remaining:
            return ClusterType.ON_DEMAND

        # 5. DANGER ZONE: Proactively use on-demand to maintain a safety buffer.
        buffer = max(self.min_buffer, self.buffer_factor * work_remaining)
        slack = time_to_deadline - work_remaining
        
        if slack < buffer:
            return ClusterType.ON_DEMAND

        # 6. ECONOMY MODE: We have enough slack, so prioritize cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide whether to wait or pay up.
            # Don't decide based on history until we have a reasonable sample.
            if not self.spot_history or len(self.spot_history) < self.history_window // 4:
                return ClusterType.NONE

            estimated_availability = sum(self.spot_history) / len(self.spot_history)

            if estimated_availability < self.min_spot_chance_to_wait:
                # Recent availability is low. Don't risk waiting.
                return ClusterType.ON_DEMAND
            else:
                # Availability seems decent. Wait for a spot instance to save money.
                return ClusterType.NONE
