import collections
import bisect

class Controller:
    """
    A controller for the Cant-Be-Late Multi-Region Scheduling Problem.
    It uses a cost-based heuristic to make decisions at each time step,
    balancing the low price of spot instances against their risk of interruption
    and the overhead cost of switching between regions.
    """

    def __init__(self, config):
        """
        Initializes the Controller with problem-specific configuration.
        """
        self.config = config
        self.regions = config['regions']
        self.on_demand_prices = config['on_demand_prices']
        self.min_on_demand_price = min(self.on_demand_prices.values())
        
        self.deadline = config['deadline']
        self.restart_overhead = config['restart_overhead']
        
        self.current_region = None
        
        # --- Policy Parameters ---
        # Window size for price history (480 steps * 3 min/step = 24 hours)
        self.WINDOW_SIZE = 480 
        # Payback period (in hours) required to justify a region switch
        self.PAYBACK_HORIZON = 2.0 
        # Minimum number of data points before trusting statistical estimates
        self.MIN_HISTORY_FOR_STATS = 20
        # A small probability added to success chance to prevent division by zero
        # and to cap the risk penalty.
        self.STABILITY_FACTOR = 0.05 
        
        # Data structures to maintain rolling statistics for spot prices
        self.price_history_deques = {
            r: collections.deque(maxlen=self.WINDOW_SIZE) for r in self.regions
        }

    def _get_percentile_rank(self, data, score):
        """
        Calculates the percentile rank of a score in a dataset.
        This is a manual implementation similar to scipy.stats.percentileofscore(kind='weak').
        """
        if not data:
            return 0.5  # Default to median if no historical data

        sorted_data = sorted(data)
        
        count_less = bisect.bisect_left(sorted_data, score)
        count_equal = bisect.bisect_right(sorted_data, score) - count_less
        
        if len(sorted_data) == 0:
            return 0.5
            
        rank = (count_less + 0.5 * count_equal) / len(sorted_data)
        return rank

    def get_next_action(self, current_time, remaining_task_duration, spot_price_history, is_spot_interrupted):
        """
        Determines the next action (region and instance type) to take.
        """
        # 1. Update historical data with the latest prices
        for r in self.regions:
            if spot_price_history.get(r):
                self.price_history_deques[r].append(spot_price_history[r][-1])

        # 2. Calculate available slack time
        slack = self.deadline - current_time - remaining_task_duration

        # 3. Emergency Mode: If slack is critically low, use on-demand to guarantee progress.
        if slack <= self.restart_overhead:
            # Choose the current region to avoid restart overhead, or a default if it's the first step.
            region_to_use = self.current_region if self.current_region else self.regions[0]
            action = (region_to_use, 'ON_DEMAND')
            self.current_region = action[0]
            return action

        # 4. Normal Mode: Analyze options to find the most cost-effective action.
        
        # a. Calculate risk-adjusted "effective prices" for spot instances in all regions.
        effective_spot_prices = {}
        for r in self.regions:
            current_spot_price = spot_price_history[r][-1]
            history = self.price_history_deques[r]
            
            if len(history) < self.MIN_HISTORY_FOR_STATS:
                # Not enough data, assume a neutral 50% success probability
                p_success = 0.5
            else:
                # Estimate interruption probability based on price's historical rank
                p_rank = self._get_percentile_rank(history, current_spot_price)
                p_success = 1.0 - p_rank
            
            # The effective price is the actual price adjusted for interruption risk.
            effective_price = current_spot_price / (p_success + self.STABILITY_FACTOR)
            effective_spot_prices[r] = effective_price

        # b. Find the best possible action/score achievable globally, ignoring switching costs.
        best_overall_score = float('inf')
        best_overall_region = None
        for r in self.regions:
            # For each region, the best score is the minimum of its effective spot price and on-demand price.
            region_best_score = min(effective_spot_prices[r], self.on_demand_prices[r])
            if region_best_score < best_overall_score:
                best_overall_score = region_best_score
                best_overall_region = r

        # c. Determine the best score achievable without switching regions.
        if self.current_region is None:
            # On the first step, we must "switch" into a region, so staying is not an option.
            best_stay_score = float('inf')
        else:
            stay_spot_score = effective_spot_prices[self.current_region]
            stay_od_score = self.on_demand_prices[self.current_region]
            best_stay_score = min(stay_spot_score, stay_od_score)

        # d. Decide whether to switch regions based on a cost-benefit analysis.
        # A hysteresis buffer prevents frequent, low-value switches.
        switch_hysteresis_buffer = (self.restart_overhead * self.min_on_demand_price) / self.PAYBACK_HORIZON
        
        if best_stay_score > best_overall_score + switch_hysteresis_buffer:
            # Decision: SWITCH to the best overall region.
            target_region = best_overall_region
        else:
            # Decision: STAY in the current region.
            target_region = self.current_region
        
        # e. In the chosen target region, decide between SPOT and ON_DEMAND.
        if effective_spot_prices[target_region] < self.on_demand_prices[target_region]:
            action = (target_region, 'SPOT')
        else:
            action = (target_region, 'ON_DEMAND')
            # Optimization: if choosing ON_DEMAND, it's never worth switching regions
            # and incurring overhead, as OD prices are very similar. Stay put if possible.
            if self.current_region is not None:
                action = (self.current_region, 'ON_DEMAND')

        # 5. Update internal state and return the chosen action.
        self.current_region = action[0]
        return action
