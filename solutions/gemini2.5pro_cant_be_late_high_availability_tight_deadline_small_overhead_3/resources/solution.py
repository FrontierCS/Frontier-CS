import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        """
        Constructor for the strategy.
        Initializes buffers for the decision logic to None. They will be
        lazily initialized in the first call to _step, once environment
        parameters like `restart_overhead` are available.
        """
        super().__init__(args)
        self.panic_buffer = None
        self.wait_buffer = None

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Returns which cluster type to use next.

        The strategy is based on a "time buffer" or "slack". The buffer is
        the amount of extra time available before the deadline, after
        accounting for the remaining work that needs to be done.

        The decision logic is divided into three zones based on the buffer size:
        1. Panic Zone (buffer is very low): Use On-Demand exclusively to
           guarantee finishing before the deadline.
        2. Aggressive Zone (buffer is large): Use Spot when available for its
           low cost. If Spot is unavailable, wait (use NONE) to save money,
           as there is ample time to spare.
        3. Conservative Zone (buffer is in-between): Use Spot when available.
           If Spot is unavailable, use On-Demand to make progress and prevent
           the buffer from shrinking, avoiding the risk of entering the panic zone.
        """
        # Lazily initialize buffer thresholds on the first call to _step.
        # This makes the strategy adaptive to the specific problem parameters.
        if self.panic_buffer is None:
            # Panic buffer: safety margin to switch to guaranteed On-Demand.
            # Set to handle multiple potential preemption events. A preemption
            # effectively costs `restart_overhead` of buffer time.
            self.panic_buffer = 5 * self.restart_overhead

        if self.wait_buffer is None:
            # Wait buffer: threshold to decide between waiting (NONE) or
            # using On-Demand when Spot is unavailable. This marks the transition
            # from the Aggressive to the Conservative zone.
            self.wait_buffer = 20 * self.restart_overhead

        # Calculate the total amount of work completed so far.
        work_done = sum(end - start for start, end in self.task_done_time)
        # Calculate the remaining work required.
        work_rem = self.task_duration - work_done

        # If the task is finished, do nothing to minimize cost.
        if work_rem <= 0:
            return ClusterType.NONE

        # Calculate the time remaining until the hard deadline.
        time_rem = self.deadline - self.env.elapsed_seconds
        
        # The buffer is the slack time we have. If we were to run the rest of
        # the job on On-Demand, this is how much time we would have to spare.
        buffer = time_rem - work_rem

        # --- Decision Logic ---

        # 1. Panic Zone check:
        # If the buffer is below the panic threshold, we must use On-Demand.
        if buffer <= self.panic_buffer:
            return ClusterType.ON_DEMAND

        # If we are not in the panic zone, we can consider using Spot.
        if has_spot:
            return ClusterType.SPOT
        
        # Spot is not available, and we are not in the panic zone.
        # The decision is between waiting or using On-Demand.
        if buffer > self.wait_buffer:
            # 2. Aggressive Zone: Ample buffer, so wait for Spot.
            return ClusterType.NONE
        else:
            # 3. Conservative Zone: Buffer is shrinking, use On-Demand to
            #    guarantee progress and preserve the remaining buffer.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """Required for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
