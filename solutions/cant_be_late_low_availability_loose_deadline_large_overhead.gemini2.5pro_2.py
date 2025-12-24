import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A slack-based scheduling strategy for the Cant-Be-Late problem.

    This strategy makes decisions based on the concept of "slack", defined as the
    amount of extra time available before the deadline, assuming all remaining
    work is completed on reliable on-demand instances.

    The decision logic operates in three modes based on the current slack:
    1. Patient Mode: When slack is plentiful, the strategy prioritizes cost savings
       by waiting for cheap Spot instances to become available (choosing NONE)
       rather than using expensive On-Demand instances.
    2. Impatient Mode: When slack falls below a `waiting_margin`, the strategy
       stops waiting and uses On-Demand instances if Spot is unavailable. This
       prevents further erosion of the slack while still preferring Spot when
       possible.
    3. Emergency Mode: When slack falls below a critical `safety_margin`, the
       strategy switches exclusively to On-Demand instances to guarantee that
       the job finishes before the deadline, avoiding a catastrophic penalty.

    The thresholds for these modes (`waiting_margin` and `safety_margin`) are
    the key parameters of this strategy. The `safety_margin` is set relative to
    the `restart_overhead` to provide a buffer against last-minute preemptions.
    """
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        self.args = args
        # These will be initialized in solve() once environment info is available.
        self.safety_margin: float = 0
        self.waiting_margin: float = 0

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        Instantiates the strategy from command-line arguments. This allows for
        hyperparameter tuning during evaluation.
        """
        parser.add_argument('--safety_margin_factor', type=float, default=1.5,
                            help='Factor of restart_overhead for the safety margin.')
        parser.add_argument('--waiting_margin_seconds', type=float, default=3600.0,
                            help='Slack threshold (in seconds) to switch from waiting to using on-demand.')
        args, _ = parser.parse_known_args()
        return cls(args)

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters. Called once before the simulation starts.
        """
        safety_margin_factor = getattr(self.args, 'safety_margin_factor', 1.5)
        waiting_margin_seconds = getattr(self.args, 'waiting_margin_seconds', 3600.0)

        # The safety margin is the critical slack threshold. Below this, we must use
        # on-demand. It's set to be larger than a single restart_overhead to ensure
        # we can recover from a preemption even when near the margin.
        self.safety_margin = self.restart_overhead * safety_margin_factor

        # The waiting margin is the slack threshold below which we become "impatient".
        # Instead of waiting for Spot, we use On-Demand to make progress.
        self.waiting_margin = waiting_margin_seconds
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision-making logic called at each timestep of the simulation.
        """
        # Calculate the total amount of work completed so far.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is done, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate the time remaining until the hard deadline.
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # Calculate slack: the time buffer we have if we run the rest of the
        # job on guaranteed on-demand instances. This is our primary state variable.
        slack = time_to_deadline - work_remaining

        # --- State-based Decision Logic ---

        # 1. Emergency Mode: If slack is critically low, we must use on-demand
        #    to guarantee completion and avoid the failure penalty.
        if slack < self.safety_margin:
            return ClusterType.ON_DEMAND

        # 2. Greedy Choice: If we have a comfortable amount of slack, always
        #    prefer the cheaper Spot instance when it's available.
        if has_spot:
            return ClusterType.SPOT

        # At this point, we have enough slack, but Spot is not available.
        # We must choose between spending money (ON_DEMAND) or spending slack (NONE).

        # 3. Impatient Mode: If slack is below our waiting margin, it's too risky
        #    to wait and burn more slack. Use on-demand to make guaranteed progress.
        if slack < self.waiting_margin:
            return ClusterType.ON_DEMAND

        # 4. Patient Mode: If slack is plentiful, we can afford to wait (do nothing)
        #    for a cheap Spot instance to become available in a future step.
        return ClusterType.NONE
