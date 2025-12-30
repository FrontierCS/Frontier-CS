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

        # --- Strategy Parameters (Tunable) ---
        self.PANIC_BUFFER_FACTOR = 3.0
        self.SWITCH_STREAK_THRESHOLD = 2
        self.WAIT_SLACK_THRESHOLD_FRACTION = 0.25
        self.SWITCH_COOLDOWN_FACTOR = 5.0
        self.COOLDOWN_PENALTY_FACTOR = 1.5

        # --- State Tracking ---
        self.last_switch_time = -float('inf')

        # --- Pre-computation of Spot Availability Traces ---
        self.spot_availability = []
        trace_files = config.get("trace_files", [])
        for trace_file in trace_files:
            with open(trace_file) as f:
                trace = [bool(int(line.strip())) for line in f]
            self.spot_availability.append(trace)
        
        self.trace_len = 0
        if self.spot_availability:
            self.trace_len = max(len(t) for t in self.spot_availability)
            for i in range(len(self.spot_availability)):
                if len(self.spot_availability[i]) < self.trace_len:
                    self.spot_availability[i].extend(
                        [False] * (self.trace_len - len(self.spot_availability[i])))
        
        self.num_regions = len(self.spot_availability)

        # Pre-calculate future spot streaks for efficiency
        self.spot_streaks = [[0] * self.trace_len for _ in range(self.num_regions)]
        if self.num_regions > 0:
            for r in range(self.num_regions):
                count = 0
                for t in range(self.trace_len - 1, -1, -1):
                    if self.spot_availability[r][t]:
                        count += 1
                    else:
                        count = 0
                    self.spot_streaks[r][t] = count
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Calculate current state variables
        time_now = self.env.elapsed_seconds
        
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - time_now
        if time_left <= 0:
            return ClusterType.ON_DEMAND
            
        current_step = int(time_now / self.env.gap_seconds)
        current_region = self.env.get_current_region()

        effective_work_left = work_left + self.remaining_restart_overhead
        
        # 2. Urgency Check (Panic Mode)
        panic_threshold = effective_work_left + self.PANIC_BUFFER_FACTOR * self.restart_overhead
        if time_left <= panic_threshold:
            return ClusterType.ON_DEMAND

        # 3. Normal Operation: Prioritize cheap spot instances
        if has_spot:
            return ClusterType.SPOT

        # 4. No spot in current region: Evaluate alternatives
        best_switch_region = -1
        max_streak = 0
        if self.num_regions > 1:
            for r in range(self.num_regions):
                if r == current_region:
                    continue
                if current_step < self.trace_len and self.spot_availability[r][current_step]:
                    streak = self.spot_streaks[r][current_step]
                    if streak > max_streak:
                        max_streak = streak
                        best_switch_region = r

        effective_switch_threshold = self.SWITCH_STREAK_THRESHOLD
        cooldown_period = self.SWITCH_COOLDOWN_FACTOR * self.restart_overhead
        if (time_now - self.last_switch_time) < cooldown_period:
            effective_switch_threshold *= self.COOLDOWN_PENALTY_FACTOR

        # Decision A: Switch to a better region
        if best_switch_region != -1 and max_streak >= effective_switch_threshold:
            self.env.switch_region(best_switch_region)
            self.last_switch_time = time_now
            return ClusterType.SPOT

        # Decision B or C: Wait (NONE) or use ON_DEMAND
        slack = time_left - effective_work_left
        wait_slack_threshold = self.deadline * self.WAIT_SLACK_THRESHOLD_FRACTION
        
        if slack > wait_slack_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND