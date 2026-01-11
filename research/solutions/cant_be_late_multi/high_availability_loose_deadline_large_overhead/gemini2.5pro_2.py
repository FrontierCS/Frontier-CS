import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that balances cost-saving with deadline-awareness.

    The strategy operates in three main modes:
    1.  **Normal Mode**: If Spot instances are available in the current region, use them.
        This is the most cost-effective way to make progress.

    2.  **Panic Mode**: If the remaining time is becoming critically short, switch to
        On-Demand instances. This guarantees progress and minimizes the risk of
        missing the deadline, which incurs a severe penalty. The decision to enter
        this mode is based on a conservative estimate of the time required to
        finish the job using only On-Demand, plus a safety buffer.

    3.  **Exploration/Wait Mode**: If Spot is not available and there's sufficient
        slack time, the strategy decides between three actions:
        a. **Explore**: If another region has a significantly higher estimated
           probability of Spot availability, switch to that region and probe its
           status. This is done by returning ClusterType.NONE for one time step.
           Probabilities are learned online using a Bayesian approach with a
           Beta(2,1) prior, reflecting the hint of high spot availability.
        b. **Wait**: If no other region looks promising but there is a large amount of
           slack time, wait in the current region (ClusterType.NONE) hoping for
           Spot to become available soon. This saves money compared to On-Demand.
        c. **Use On-Demand**: If slack is not large enough to risk waiting or
           exploring, use On-Demand to ensure progress is made.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
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

        # Custom initialization
        self.num_regions = len(config["trace_files"])

        # Bayesian prior for spot availability probability.
        # We use a Beta(alpha=2, beta=1) prior, giving an expected probability of
        # 2/3. This incorporates the problem's hint that spot availability is high.
        # alpha = number of successes (spot available) + 1
        # beta = number of failures (spot unavailable) + 1
        # For a Beta(2,1) prior, we initialize with 2 hits and 1 miss.
        # alpha = 2, beta = 1.
        self.spot_hits = [2] * self.num_regions   # Represents alpha
        self.probes = [3] * self.num_regions    # Represents alpha + beta

        # To avoid double-counting stats if _step is called multiple times
        # at the same simulated time.
        self.last_probed_time = {}  # {region_idx: time}

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Update statistics based on the current observation
        current_region = self.env.get_current_region()
        current_time = self.env.elapsed_seconds

        if self.last_probed_time.get(current_region, -1) < current_time:
            self.probes[current_region] += 1
            if has_spot:
                self.spot_hits[current_region] += 1
            self.last_probed_time[current_region] = current_time

        # 2. Calculate current state variables
        remaining_work = self.task_duration - sum(self.task_done_time)

        # If the task is finished, do nothing to save cost.
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - current_time

        # 3. PANIC MODE: Switch to On-Demand if the deadline is approaching
        is_on_demand = (last_cluster_type == ClusterType.ON_DEMAND)
        # Conservatively estimate overhead: assume any change incurs it.
        overhead_if_od = 0 if is_on_demand else self.restart_overhead
        time_needed_od = remaining_work + overhead_if_od

        # Safety buffer to account for potential spot preemptions or other delays.
        # A buffer of 2 hours (2 * gap_seconds) allows for recovery from a failed
        # exploration attempt plus a preemption.
        panic_buffer = 2 * self.env.gap_seconds

        if time_left <= time_needed_od + panic_buffer:
            return ClusterType.ON_DEMAND

        # 4. NORMAL MODE: If Spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # 5. SPOT NOT AVAILABLE: Decide between ON_DEMAND, NONE (wait), or SWITCH+NONE (explore)
        slack = time_left - (time_needed_od + panic_buffer)

        # 5a. Evaluate exploration (switching to another region)
        # A probe (switch + NONE) costs one time step plus restart overhead.
        exploration_time_cost = self.env.gap_seconds + self.restart_overhead
        if slack > exploration_time_cost:
            probs = [(self.spot_hits[i] / self.probes[i]) for i in range(self.num_regions)]

            best_alt_region = -1
            max_prob = -1.0
            for i in range(self.num_regions):
                if i == current_region:
                    continue
                if probs[i] > max_prob:
                    max_prob = probs[i]
                    best_alt_region = i

            # Heuristics to decide if a switch is worthwhile
            prob_gain_threshold = 0.15  # Other region must be this much better
            min_prob_threshold = 0.5    # Don't switch to a region with low expected prob

            if (best_alt_region != -1 and
                max_prob > probs[current_region] + prob_gain_threshold and
                max_prob > min_prob_threshold):
                self.env.switch_region(best_alt_region)
                return ClusterType.NONE  # Probe the new region

        # 5b. If not exploring, decide between waiting (NONE) or working (ON_DEMAND)
        # If slack is large, we can afford to wait for spot to reappear.
        wait_slack_threshold = 5 * self.env.gap_seconds
        if slack > wait_slack_threshold:
            return ClusterType.NONE

        # If slack is not large enough to wait, and we're not exploring,
        # we must make progress using On-Demand to be safe.
        return ClusterType.ON_DEMAND