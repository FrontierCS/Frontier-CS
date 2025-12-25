import sys

class Solver:
    """
    Solver for the Cant-Be-Late Multi-Region Scheduling Problem.
    It uses dynamic programming to find the minimum-cost schedule.
    """

    def __init__(self, task_duration, deadline, on_demand_price, restart_overhead, spot_traces):
        self.task_duration = task_duration
        self.deadline = deadline
        self.on_demand_price = on_demand_price
        self.restart_overhead = restart_overhead
        self.spot_traces = spot_traces
        self.num_regions = len(spot_traces)

        # Discretize work units to convert the problem into an integer-based DP.
        # A common divisor for work amounts (1.0, 1.0-overhead) is 0.05.
        self.WORK_UNIT = 0.05
        self.total_work_units = self._work_to_units(self.task_duration)
        self.units_per_hour = self._work_to_units(1.0)
        self.overhead_units = self._work_to_units(self.restart_overhead)

        # The DP state depends on the previously used region.
        # We use a special index for the case where no region was used (initial/idle).
        self.prev_region_idx_none = self.num_regions

        # DP tables are stored in flat lists for performance.
        # Strides are pre-calculated for quick index computation.
        self.t_dim = self.deadline + 1
        self.w_dim = self.total_work_units + 1
        self.p_dim = self.num_regions + 1

        self.w_stride = self.p_dim
        self.t_stride = self.w_dim * self.p_dim

        table_size = self.t_dim * self.w_dim * self.p_dim
        self.dp = [float('inf')] * table_size
        self.policy = [(None, None)] * table_size

        self._compute_policy()

    def _get_idx(self, t, w, p):
        """Calculates the index into the flat DP tables."""
        return t * self.t_stride + w * self.w_stride + p

    def _work_to_units(self, work_hours):
        """Converts continuous work hours to discrete units."""
        return int(round(work_hours / self.WORK_UNIT))

    def _compute_policy(self):
        """
        Fills the DP table backwards in time to find the optimal policy.
        The state is (time, remaining_work, previous_region).
        """
        for t in range(self.deadline, -1, -1):
            for w_units in range(self.total_work_units + 1):
                for prev_region_idx in range(self.num_regions + 1):
                    idx = self._get_idx(t, w_units, prev_region_idx)

                    # Base case: Work is completed. Cost is 0.
                    if w_units == 0:
                        self.dp[idx] = 0
                        continue

                    # Base case: Deadline reached with work remaining. Cost is infinite.
                    if t == self.deadline:
                        continue

                    min_cost = float('inf')
                    best_action = (None, None)

                    # Decision 1: Be idle.
                    # Cost is 0 for this step. Next state has no previous region.
                    idle_idx = self._get_idx(t + 1, w_units, self.prev_region_idx_none)
                    cost_idle = self.dp[idle_idx]
                    if cost_idle < min_cost:
                        min_cost = cost_idle
                        best_action = (None, None)

                    prev_region_id = prev_region_idx if prev_region_idx < self.num_regions else None

                    # Decision 2: Run a job in a region.
                    for region_id in range(self.num_regions):
                        is_startup = (prev_region_id is None)
                        is_switching = (not is_startup and region_id != prev_region_id)

                        work_this_hour_units = self.units_per_hour
                        if is_startup or is_switching:
                            work_this_hour_units -= self.overhead_units
                        work_this_hour_units = max(0, work_this_hour_units)

                        # Option 2a: On-demand instance
                        next_w_units_od = max(0, w_units - work_this_hour_units)
                        future_idx_od = self._get_idx(t + 1, next_w_units_od, region_id)
                        future_cost_od = self.dp[future_idx_od]
                        if future_cost_od != float('inf'):
                            total_cost_od = self.on_demand_price + future_cost_od
                            if total_cost_od < min_cost:
                                min_cost = total_cost_od
                                best_action = (region_id, 'on_demand')

                        # Option 2b: Spot instance
                        spot_price = self.spot_traces[region_id]['price'][t]
                        is_available = self.spot_traces[region_id]['available'][t] == 1

                        work_spot_units = work_this_hour_units if is_available else 0
                        next_w_units_spot = max(0, w_units - work_spot_units)
                        future_idx_spot = self._get_idx(t + 1, next_w_units_spot, region_id)
                        future_cost_spot = self.dp[future_idx_spot]
                        if future_cost_spot != float('inf'):
                            total_cost_spot = spot_price + future_cost_spot
                            if total_cost_spot < min_cost:
                                min_cost = total_cost_spot
                                best_action = (region_id, 'spot')

                    self.dp[idx] = min_cost
                    self.policy[idx] = best_action

    def solve(self, remaining_work, time_step, current_region_id):
        """
        Provides the optimal action for the given state by looking up the pre-computed policy.
        """
        # If work is done, do nothing. Use a small epsilon for float comparison.
        if remaining_work <= 1e-9:
            return None, None

        # Fallback for being called past the deadline.
        if time_step >= self.deadline:
            return 0, 'on_demand'

        w_units = self._work_to_units(remaining_work)
        # Clamp work units to the table's bounds to handle float inaccuracies.
        w_units = min(w_units, self.total_work_units)

        if current_region_id is None:
            prev_region_idx = self.prev_region_idx_none
        else:
            prev_region_idx = current_region_id

        idx = self._get_idx(time_step, w_units, prev_region_idx)
        return self.policy[idx]
