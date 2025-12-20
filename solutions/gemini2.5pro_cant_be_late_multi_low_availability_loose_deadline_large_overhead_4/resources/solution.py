import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        self.num_regions = self.env.get_num_regions()
        
        # EMA of spot availability for each region. Start with a neutral 0.5.
        self.ema_spot = [0.5] * self.num_regions
        self.alpha = 0.1

        # State tracking
        self.last_history_update_time = -1.0
        self.last_switch_time = -1.0
        
        # Slack management: defines a "glide path" for the schedule
        self.initial_slack = self.deadline - self.task_duration
        if self.initial_slack < 0:
            self.initial_slack = 0

        # Tuned Hyperparameters
        # Safety factor for entering absolute critical mode
        self.SAFETY_FACTOR = 1.15
        # Required EMA improvement to justify a region switch
        self.SWITCH_IMPROVEMENT_THRESHOLD = 0.2
        # Cooldown period after a switch to prevent thrashing
        self.switch_cooldown = 5 * self.restart_overhead
        # Minimum slack required to consider switching regions
        self.SWITCH_SLACK_FACTOR = 2.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. GATHER STATE
        current_region = self.env.get_current_region()
        elapsed_time = self.env.elapsed_seconds
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        # 2. UPDATE HISTORY (Exponential Moving Average)
        if elapsed_time > self.last_history_update_time:
            spot_observation = 1.0 if has_spot else 0.0
            self.ema_spot[current_region] = (self.alpha * spot_observation) + \
                                            ((1 - self.alpha) * self.ema_spot[current_region])
            self.last_history_update_time = elapsed_time

        # 3. CALCULATE TIME PRESSURE AND SLACK
        remaining_time = self.deadline - elapsed_time
        time_needed_od = remaining_work

        # The "glide path": how much buffer we should ideally have at this point.
        if self.task_duration > 0:
            desired_slack = self.initial_slack * (remaining_work / self.task_duration)
        else:
            desired_slack = self.initial_slack
        current_slack = remaining_time - time_needed_od
        
        # Determine if we are in an absolute critical situation.
        is_critical_abs = (remaining_time <= time_needed_od * self.SAFETY_FACTOR)
        
        # 4. DECISION LOGIC
        
        # 4.1. CRITICAL MODE: Prioritize guaranteed progress above all else.
        if is_critical_abs:
            if has_spot:
                # Switching to Spot from OD incurs an overhead, which is too risky in critical mode.
                if last_cluster_type == ClusterType.ON_DEMAND:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # 4.2. NORMAL MODE: Balance cost and progress.
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switching from OD to Spot incurs an overhead.
                # Only do it if we have enough slack to absorb the time loss.
                if current_slack > desired_slack + self.restart_overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND # Not enough buffer, stay safe.
            else:
                return ClusterType.SPOT
        
        # --- Normal Mode, Spot NOT available ---
        # Options: Switch Region, use On-Demand, or Wait (None).

        # 4.2.1. CONSIDER SWITCHING REGION
        best_other_region = -1
        max_ema = -1.0
        for i in range(self.num_regions):
            if i == current_region:
                continue
            if self.ema_spot[i] > max_ema:
                max_ema = self.ema_spot[i]
                best_other_region = i
        
        can_switch = (elapsed_time - self.last_switch_time) >= self.switch_cooldown
        should_switch = (best_other_region != -1 and 
                         max_ema > self.ema_spot[current_region] + self.SWITCH_IMPROVEMENT_THRESHOLD)
        is_affordable = current_slack > self.restart_overhead * self.SWITCH_SLACK_FACTOR

        if can_switch and should_switch and is_affordable:
            self.env.switch_region(best_other_region)
            self.last_switch_time = elapsed_time
            # After a switch, wait one step to observe the new region's spot status
            # without committing to an expensive OD instance blindly.
            return ClusterType.NONE

        # 4.2.2. ON-DEMAND vs. NONE (if not switching)
        if current_slack < desired_slack:
            # We are falling behind our schedule. Use On-Demand to catch up.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack. We can afford to wait for a Spot instance.
            return ClusterType.NONE
