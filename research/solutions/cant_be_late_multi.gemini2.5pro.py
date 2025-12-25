import math

DEFAULT_ON_DEMAND_PRICE = 3.06

class CantBeLateMultiRegionPolicy:
    """
    A policy for the Cant-Be-Late Multi-Region Scheduling Problem.

    This policy uses a dynamic programming approach to find the optimal
    scheduling decision at each time step. It aims to minimize the expected
    total cost, considering spot prices, preemption probabilities, restart
    overheads, and a penalty for missing the deadline.

    The core of the policy is a recursive solver with memoization that calculates
    the minimum expected future cost for any given state (time, remaining work,
    previous region).

    To handle the uncertainty of future prices and preemptions, the policy builds
    a simple predictive model from the historical data observed during the
    simulation. It maintains statistics for prices and preemption rates for
    each region and each hour of the day, falling back to recent data when
    hour-specific history is unavailable.
    """

    def __init__(
        self,
        task_duration: float,
        deadline: int,
        restart_overhead: float,
        region_names: list[str],
    ):
        """
        Initializes the policy with the problem parameters.
        """
        self.task_duration = float(task_duration)
        self.deadline = int(deadline)
        self.restart_overhead = float(restart_overhead)
        self.region_names = list(region_names)
        self.num_regions = len(region_names)
        self.on_demand_price = DEFAULT_ON_DEMAND_PRICE

        # --- DP Discretization Setup ---
        # We discretize the work into small units. The unit size is chosen to be a
        # common divisor of 1.0 (one hour of work) and the restart overhead,
        # ensuring all work calculations are exact in this discretized space.
        # For this problem, 0.05 is the finest grain needed and works for all variants.
        self.work_unit = 0.05
        self.total_work_units = int(round(self.task_duration / self.work_unit))
        self.overhead_units = int(round(self.restart_overhead / self.work_unit))
        self.hour_work_units = int(round(1.0 / self.work_unit))

        # --- State Tracking ---
        # -1 represents a "no region" state (initial, paused, or after preemption)
        self.last_chosen_region_idx = -1
        self.current_prices = [0.0] * self.num_regions

        # --- Predictive Model Data Structures ---
        # We store historical data per hour of the day (0-23) to capture daily patterns.
        # Price history: list of observed prices for each (hour_of_day, region)
        self.price_history_per_hod = [[[] for _ in range(self.num_regions)] for _ in range(24)]
        # Preemption stats: (success_count, total_attempts) for each (hour_of_day, region)
        self.preemption_stats_per_hod = [[(0, 0) for _ in range(self.num_regions)] for _ in range(24)]

        # --- DP Memoization ---
        # The memoization table for our DP solver.
        self.memo = {}
        # The DP table is only valid for the current time_step, as predictions change.
        self.memo_time_step = -1

    def get_action(
        self,
        time_step: int,
        remaining_work: float,
        region_data: list[dict],
        was_interrupted: bool,
    ) -> str | None:
        """
        Determines the best action (which region to run in, or pause) for the current time step.
        """
        # 1. Update history and models with the outcome of the previous time step.
        if time_step > 0:
            self._update_models(time_step - 1, was_interrupted)

        # 2. Record current market data for the current time step.
        self._record_current_data(time_step, region_data)

        # 3. Solve the DP to find the optimal policy from the current state.
        remaining_work_units = int(round(remaining_work / self.work_unit))
        
        if time_step != self.memo_time_step:
            self.memo.clear()
            self.memo_time_step = time_step

        _cost, best_action_idx = self._solve_dp(time_step, remaining_work_units, self.last_chosen_region_idx)

        # 4. Update internal state and return the chosen action.
        self.last_chosen_region_idx = best_action_idx

        if best_action_idx == -1:
            return None
        return self.region_names[best_action_idx]

    def _update_models(self, prev_time_step: int, was_interrupted: bool):
        """Updates the predictive models based on the outcome of the last action."""
        hod = prev_time_step % 24
        
        if self.last_chosen_region_idx != -1:
            region_idx = self.last_chosen_region_idx
            s_count, t_count = self.preemption_stats_per_hod[hod][region_idx]
            t_count += 1
            if not was_interrupted:
                s_count += 1
            self.preemption_stats_per_hod[hod][region_idx] = (s_count, t_count)
        
        if was_interrupted:
            self.last_chosen_region_idx = -1

    def _record_current_data(self, time_step: int, region_data: list[dict]):
        """Records the latest market prices."""
        hod = time_step % 24
        self.current_prices = [d['spot_price'] for d in region_data]
        for r_idx in range(self.num_regions):
            self.price_history_per_hod[hod][r_idx].append(self.current_prices[r_idx])

    def _predict(self, future_time_step: int, region_idx: int) -> tuple[float, float]:
        """Predicts (price, preemption_probability) for a future time and region."""
        hod = future_time_step % 24
        
        prices = self.price_history_per_hod[hod][region_idx]
        if prices:
            prices.sort()
            predicted_price = prices[len(prices) // 2]
        else:
            predicted_price = self.current_prices[region_idx]

        s_count, t_count = self.preemption_stats_per_hod[hod][region_idx]
        predicted_prob = (t_count - s_count + 1) / (t_count + 2.0)

        return predicted_price, predicted_prob

    def _solve_dp(self, t: int, w_units: int, prev_r_idx: int) -> tuple[float, int]:
        """
        Recursively calculates the minimum expected future cost and the best action.
        
        State: (t, w_units, prev_r_idx)
        Returns: (min_expected_cost, best_action_index)
        """
        if w_units <= 0:
            return 0.0, -1
        if t >= self.deadline:
            cost = w_units * self.work_unit * self.on_demand_price
            return cost, -1

        state = (t, w_units, prev_r_idx)
        if state in self.memo:
            return self.memo[state]

        cost_pause, _ = self._solve_dp(t + 1, w_units, -1)
        best_cost = cost_pause
        best_action = -1

        for r_idx in range(self.num_regions):
            price, preemption_prob = self._predict(t, r_idx)
            
            is_switch = (prev_r_idx != -1 and prev_r_idx != r_idx)
            overhead = self.overhead_units if is_switch else 0
            work_done_if_ok = self.hour_work_units - overhead

            if work_done_if_ok <= 0:
                continue

            cost_succ, _ = self._solve_dp(t + 1, w_units - work_done_if_ok, r_idx)
            cost_fail, _ = self._solve_dp(t + 1, w_units, -1)
            
            expected_cost_run = (1 - preemption_prob) * (price + cost_succ) + preemption_prob * cost_fail

            if expected_cost_run < best_cost:
                best_cost = expected_cost_run
                best_action = r_idx
        
        self.memo[state] = (best_cost, best_action)
        return best_cost, best_action
