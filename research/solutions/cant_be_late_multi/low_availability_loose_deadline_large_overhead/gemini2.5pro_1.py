import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by using Spot
    instances opportunistically while ensuring the task finishes before the deadline.

    The strategy works as follows:
    1.  **Pre-computation (`solve`):**
        -   Loads all region-specific spot availability traces.
        -   For each trace and each timestep, it pre-computes the length of the
            consecutive upcoming window of spot availability. This allows for
            O(1) lookups of future spot potential during the simulation.

    2.  **Decision Making (`_step`):**
        -   **State Calculation:** At each step, it calculates the remaining work
            and the time left until the deadline. It uses an incremental sum to
            track work done efficiently.
        -   **Panic Mode:** It first checks if the time remaining is critically
            low. If the time required to finish the rest of the job using
            only reliable on-demand instances exceeds the time left, it enters
            a "panic mode" and exclusively uses on-demand instances to guarantee
            completion.
        -   **Normal Operation:** If there is sufficient time slack, it seeks
            the best spot instance opportunity.
            - It evaluates the pre-computed future spot availability for the
              current region and all other regions.
            - It prefers to stay in the current region if its spot availability
              is as good as or better than any other region, to avoid the
              cost of switching.
            - If another region offers a strictly better spot window, it
              evaluates if a switch is worthwhile.
            - **Switching Heuristic:** A switch is considered worthwhile only if:
                a) There is enough time slack to absorb the restart overhead
                   incurred by the switch.
                b) The expected duration of the spot window in the target
                   region is longer than the restart overhead time, implying
                   a net gain in productive, low-cost time.
        -   **No Spot:** If no spot instances are available in any region, it
            falls back to using an on-demand instance to ensure progress.
        -   **Task Completion:** Once the task is finished, it returns `NONE` to
            stop incurring costs.
    """

    NAME = "lookahead_optimizer"

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

        # Load traces from files
        self.traces = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    # Assuming format is one integer (0 or 1) per line
                    trace = [bool(int(line.strip())) for line in f if line.strip()]
                self.traces.append(trace)

        if not self.traces:
            self.num_regions = 0
            self.num_steps = 0
        else:
            self.num_regions = len(self.traces)
            self.num_steps = len(self.traces[0])

        # Pre-calculate future consecutive spot availability for O(1) lookup
        self.future_spot = [[0] * (self.num_steps + 1) for _ in range(self.num_regions)]
        if self.num_steps > 0:
            for r in range(self.num_regions):
                for i in range(self.num_steps - 1, -1, -1):
                    if self.traces[r][i]:
                        self.future_spot[r][i] = 1 + self.future_spot[r][i + 1]
                    else:
                        self.future_spot[r][i] = 0

        # For efficient calculation of work done
        self.my_work_done = 0.0
        self.last_task_done_len = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Calculate current state efficiently
        # Instead of sum(self.task_done_time) which is O(N), update incrementally.
        new_len = len(self.task_done_time)
        if new_len > self.last_task_done_len:
            for i in range(self.last_task_done_len, new_len):
                self.my_work_done += self.task_done_time[i]
        self.last_task_done_len = new_len
        
        work_done = self.my_work_done
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # Time to finish using on-demand from now, in the current region
        time_to_finish_od_noswitch = work_remaining + self.remaining_restart_overhead
        
        # 2. PANIC MODE: Check if we are forced to use ON_DEMAND to meet the deadline
        if time_left <= time_to_finish_od_noswitch:
            return ClusterType.ON_DEMAND

        # 3. NORMAL MODE: We have some slack, try to use SPOT
        # Determine current timestep index
        if self.env.gap_seconds == 0:
            current_step = 0
        else:
            current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        
        if current_step >= self.num_steps or self.num_regions == 0:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        # Evaluate staying in the current region
        current_future_spot = 0
        if has_spot:
            current_future_spot = self.future_spot[current_region][current_step]

        # Evaluate switching to the best alternative region
        best_other_region = -1
        max_other_future_spot = 0
        for r in range(self.num_regions):
            if r == current_region:
                continue
            if self.traces[r][current_step]:
                future_availability = self.future_spot[r][current_step]
                if future_availability > max_other_future_spot:
                    max_other_future_spot = future_availability
                    best_other_region = r
        
        # 4. DECISION LOGIC
        # Prefer staying if the current region is at least as good as any other
        if current_future_spot >= max_other_future_spot:
            if current_future_spot > 0:
                return ClusterType.SPOT
            else:
                # No spot available anywhere
                return ClusterType.ON_DEMAND
        else:
            # Another region is strictly better. Consider switching.
            # Risk assessment: Can we afford the time cost of a switch?
            time_to_finish_od_switch = work_remaining + self.restart_overhead
            if time_left <= time_to_finish_od_switch:
                 return ClusterType.ON_DEMAND

            # Reward assessment: Is the spot window long enough to be worth it?
            if max_other_future_spot * self.env.gap_seconds > self.restart_overhead:
                self.env.switch_region(best_other_region)
                return ClusterType.SPOT
            else:
                # Switch is not worth the overhead. Use On-Demand for now.
                return ClusterType.ON_DEMAND