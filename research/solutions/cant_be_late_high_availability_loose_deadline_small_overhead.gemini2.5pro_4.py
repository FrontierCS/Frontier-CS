import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy operates on a "required progress rate" principle. It continuously
    evaluates if a cost-saving approach (waiting for Spot) is still feasible
    or if a guaranteed-progress approach (On-Demand) is necessary to meet the deadline.

    Core Logic:
    1. Always use Spot instances when they are available, as this is the cheapest
       way to make progress.
    2. When Spot is unavailable, a decision is made:
       a. Calculate the projected time needed to finish the remaining work assuming
          an average Spot availability. This is our "optimistic" timeline.
       b. If the actual time remaining to the deadline is less than this
          projected time (plus a safety buffer), it means we are falling behind
          a sustainable schedule. In this case, we must use On-Demand to catch up.
       c. If we have ample time remaining, we can afford to wait for Spot to
          become available again, so we choose to do nothing (NONE).

    This creates a dynamic threshold that starts by being aggressive about making
    progress (using On-Demand to supplement Spot) and then relaxes to a more
    cost-saving mode once a sufficient time buffer has been established.
    """
    NAME = "my_solution"

    # --- Tunable Parameters ---

    # The assumed average availability of Spot instances. The problem states a
    # range of 43-78%. The midpoint is a neutral assumption. A higher value
    # makes the strategy more cost-saving but riskier on low-availability traces.
    P_SPOT_AVG = (0.43 + 0.78) / 2.0  # = 0.605

    # A fixed time buffer. We switch to On-Demand if our projected finish time
    # (based on P_SPOT_AVG) gets within this buffer of the deadline. This adds
    # robustness against unexpectedly long spot outages.
    SAFETY_BUFFER_SECONDS = 2 * 3600.0  # 2 hours

    # A multiplicative safety margin for the remaining work. This accounts for
    # time that will be lost to restart overheads, which effectively increases
    # the total wall-clock time required. A 3% margin budgets for ~29 restarts.
    SAFETY_MARGIN = 0.03

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        # No file-based configuration or complex initialization needed.
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # 1. Calculate current progress state
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is finished, do nothing.
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        # 2. Greedy choice: Always prioritize using Spot if it's available.
        # It is the most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # 3. If Spot is not available, decide whether to wait (NONE) or
        #    use On-Demand (expensive but guaranteed progress).
        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # Emergency stopgap: If time left is less than work left, we have
        # no choice but to use the 100% reliable resource (On-Demand).
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # Decision logic: Switch to On-Demand if waiting for Spot is too risky.
        # Risk is determined by comparing the time remaining vs. the time needed
        # under our assumed average Spot availability.

        # Estimate the time needed to finish if we rely on a spot-seeking
        # strategy (i.e., Spot when available, None otherwise).
        # We add a margin to the work to account for future restart overheads.
        risk_adjusted_work_rem = work_remaining * (1.0 + self.SAFETY_MARGIN)
        
        # On average, to get W work done with a resource of availability P,
        # it takes W/P time.
        time_needed_via_spot_strategy = risk_adjusted_work_rem / self.P_SPOT_AVG

        # If the actual time we have left is less than the time our spot
        # strategy is projected to need (plus a safety buffer), it's too risky
        # to wait.
        if time_to_deadline <= time_needed_via_spot_strategy + self.SAFETY_BUFFER_SECONDS:
            # We are behind schedule for a pure spot-seeking strategy.
            # Use On-Demand to make up the deficit and avoid falling further behind.
            return ClusterType.ON_DEMAND
        else:
            # We have enough of a time advantage ("slack") that we can
            # afford to wait for Spot to become available again. This is cheaper.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for evaluator instantiation.
        """
        # This method could be extended to allow command-line tuning of
        # parameters, but for this submission, we use the hardcoded class constants.
        args, _ = parser.parse_known_args()
        return cls(args)