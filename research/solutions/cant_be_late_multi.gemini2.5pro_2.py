import math

class MultiRegionSpotScheduler:
    """
    A scheduler for managing a long-running task on multi-region spot instances.
    The goal is to complete the task by a deadline while minimizing cost.
    """

    def __init__(self, task_duration: float, on_demand_price: float, spot_price: float, n_regions: int, deadline: float, restart_overhead: float, time_limit: float):
        """
        Initializes the scheduler with problem parameters.
        """
        self.task_duration = task_duration
        self.on_demand_price = on_demand_price
        self.spot_price = spot_price
        self.n_regions = n_regions
        self.deadline = deadline
        self.restart_overhead = restart_overhead
        
        # --- State Tracking ---
        self.progress: float = 0.0
        self.last_t: float = 0.0
        
        # State from the PREVIOUS interval, used to calculate progress in the CURRENT interval.
        # -2 is a sentinel for the initial state before any decision has been made.
        # None corresponds to an on-demand decision.
        # An integer corresponds to a spot region decision.
        self.prev_decision: int | None = -2
        self.prev_running_region: int | None = -2

    def schedule(self, t: float, spot_data: dict[int, bool], running_region: int | None) -> int | None:
        """
        Makes a scheduling decision at a given time t.

        Args:
            t: The current time.
            spot_data: A dictionary indicating spot availability in each region.
            running_region: The region where a spot instance was running in the last
                            interval, or None if no spot instance was running.

        Returns:
            An integer region index to run a spot instance, or None to run on-demand.
        """
        # 1. Update progress based on the outcome of the last decision interval.
        if t > self.last_t:
            dt = t - self.last_t
            work_done_in_interval = 0.0
            
            # Case A: We chose to run on-demand in the last interval.
            if self.prev_decision is None:
                work_done_in_interval = dt
            
            # Case B: We chose to run on a spot instance.
            elif isinstance(self.prev_decision, int) and self.prev_decision >= 0:
                # Progress is made only if the chosen spot instance was actually running.
                if running_region is not None and self.prev_decision == running_region:
                    # A new run (from idle/on-demand or a switch from another region)
                    # incurs a restart overhead.
                    is_new_run = (self.prev_running_region != running_region)
                    
                    if is_new_run:
                        work_done_in_interval = max(0.0, dt - self.restart_overhead)
                    else:
                        work_done_in_interval = dt
            
            self.progress += work_done_in_interval

        # If the task is finished, we can be idle to save cost.
        # To be idle, we request a region that is likely unavailable.
        if self.progress >= self.task_duration:
            decision = 0  # Requesting region 0 is a simple idle strategy.
            self.last_t = t
            self.prev_decision = decision
            self.prev_running_region = running_region
            return decision

        # 2. Make a scheduling decision for the next interval.
        work_rem = self.task_duration - self.progress
        time_rem = self.deadline - t
        
        # If we are past the deadline and not finished, we must use on-demand.
        if time_rem <= 0:
            decision = None
            self.last_t = t
            self.prev_decision = decision
            self.prev_running_region = running_region
            return decision

        # Slack is the amount of idle time we can afford. If it's zero or negative,
        # we must work continuously to meet the deadline.
        current_slack = time_rem - work_rem

        available_regions = [r for r, is_up in spot_data.items() if is_up]
        
        decision: int | None
        
        # The core heuristic: we need at least `restart_overhead` of slack to
        # safely perform a switch to a new spot instance without falling behind.
        slack_threshold = self.restart_overhead

        # --- Decision Logic: A priority-based heuristic ---

        # Priority 1: Stay on the current, cheap, running spot instance.
        if running_region is not None and running_region in available_regions:
            decision = running_region
        
        # Priority 2: Switch to a new spot instance if available and affordable.
        elif len(available_regions) > 0:
            if current_slack > slack_threshold:
                # We can afford the time cost of a switch. Pick the lowest index region.
                decision = min(available_regions)
            else:
                # Not enough slack to absorb the switch overhead. Fall back to on-demand.
                decision = None
        
        # Priority 3: No spot available. Decide between on-demand and waiting (idle).
        else: # len(available_regions) == 0
            if current_slack > slack_threshold:
                # We have enough slack to wait and still be able to switch later.
                # To wait/idle, request an unavailable region (any index is fine here).
                decision = 0
            else:
                # Not enough slack. We must run on-demand to build slack and make progress.
                decision = None

        # 3. Update state for the next call and return the decision.
        self.last_t = t
        self.prev_decision = decision
        self.prev_running_region = running_region
        
        return decision
