import json
from argparse import Namespace
from collections import deque

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A dynamic, deadline-aware scheduling strategy for multi-region spot markets.
    It prioritizes meeting the deadline while minimizing costs by opportunistically
    using spot instances, intelligently switching regions based on historical
    availability, and waiting during spot droughts if there is sufficient slack time.
    """

    NAME = "dynamic_deadline_v1"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from the problem specification file.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # State and hyperparameters are initialized here. Some are set to None
        # and will be fully initialized in the first call to _step, as they
        # depend on the `self.env` object created in super().__init__.
        self.spot_history = None
        self.spot_risk_buffer = None

        # --- Hyperparameters ---
        # The number of past time steps to consider for spot availability.
        self.history_len = 24
        # A new region's reliability score must exceed the current region's score
        # by this threshold to trigger a switch.
        self.switch_threshold = 0.25
        # An initial reliability score for unexplored regions. Given the problem
        # states low spot availability, this is set below 0.5.
        self.unexplored_region_score = 0.4

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action (which cluster type to use, and whether to switch region)
        based on the current state of the system.
        """
        # Lazy initialization of state that depends on the environment.
        if self.spot_history is None:
            num_regions = self.env.get_num_regions()
            self.spot_history = [deque(maxlen=self.history_len) for _ in range(num_regions)]
            # Define the safety buffer for using Spot. We must have enough time to
            # recover from an immediate preemption (restart_overhead) plus the loss
            # of progress in the current time step (gap_seconds).
            self.spot_risk_buffer = self.restart_overhead + self.env.gap_seconds

        # 1. Update historical data with the latest spot availability.
        current_region = self.env.get_current_region()
        self.spot_history[current_region].append(1 if has_spot else 0)

        # 2. Calculate current progress and time constraints.
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        # If the task is already finished, do nothing to save costs.
        if work_left <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 3. SAFETY NET: A crucial check to ensure the deadline is met.
        # Calculate the time required to finish if we switch to the reliable
        # On-Demand instances starting from this step in the current region.
        time_needed_od_here = work_left
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_od_here += self.restart_overhead

        if time_needed_od_here >= time_to_deadline:
            # If the time required is greater than or equal to the time remaining,
            # we have no choice but to use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # 4. Main Decision Logic: We have some slack time.
        if has_spot:
            # Spot is available. Use it if the potential time loss from a preemption
            # does not jeopardize the deadline.
            time_needed_if_spot_fails = work_left + self.restart_overhead
            if time_to_deadline > time_needed_if_spot_fails + self.spot_risk_buffer:
                # Sufficient slack exists to absorb a potential failure. Use cheap Spot.
                return ClusterType.SPOT
            else:
                # Slack is too low. The risk of preemption is too high. Use On-Demand.
                return ClusterType.ON_DEMAND
        else:
            # Spot is not available in the current region.
            # Consider switching region, using On-Demand, or waiting.
            
            # Evaluate switching to a new region.
            scores = []
            for r_hist in self.spot_history:
                if len(r_hist) > 0:
                    scores.append(sum(r_hist) / len(r_hist))
                else:
                    scores.append(self.unexplored_region_score)
            
            current_score = scores[current_region]
            best_other_score = -1.0
            best_other_region = -1

            for i, score in enumerate(scores):
                if i != current_region and score > best_other_score:
                    best_other_score = score
                    best_other_region = i
            
            time_needed_after_switch = work_left + self.restart_overhead
            
            if (best_other_region != -1 and
                    best_other_score > current_score + self.switch_threshold and
                    time_to_deadline > time_needed_after_switch + self.env.gap_seconds):
                
                # A significantly better region exists and we have time for the switch.
                self.env.switch_region(best_other_region)
                # After switching, use On-Demand as a safe default to make progress.
                return ClusterType.ON_DEMAND

            # If not switching, decide between waiting (NONE) and working (ON_DEMAND).
            slack = time_to_deadline - work_left
            # We can only wait if the slack is enough to cover a lost time step
            # plus a future potential restart overhead.
            wait_threshold = self.restart_overhead + self.env.gap_seconds

            if slack > wait_threshold:
                # Plenty of slack. It's cost-effective to wait for Spot to return.
                return ClusterType.NONE
            else:
                # Not enough slack to afford waiting. Must make progress with On-Demand.
                return ClusterType.ON_DEMAND