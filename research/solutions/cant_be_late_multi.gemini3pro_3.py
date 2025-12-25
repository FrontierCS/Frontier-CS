import math

class Scheduler:
    def __init__(self, task_duration, deadline, overhead):
        self.task_duration = float(task_duration)
        self.deadline = float(deadline)
        self.overhead = float(overhead)
        self.current_region = None
        self.current_action = None
        self.od_price = 3.06  # Estimated on-demand price

    def schedule(self, time, progress, prices):
        remaining_work = self.task_duration - progress

        if remaining_work <= 1e-6:
            return 'stop', None

        # Calculate slack to determine if we need to force On-Demand (OD)
        # We assume switching to OD might incur overhead if we aren't already running it
        # (Worst case assumption for safety)
        switch_penalty = self.overhead if self.current_action != 'on_demand' else 0.0
        time_to_finish = remaining_work + switch_penalty
        time_left = self.deadline - time
        slack = time_left - time_to_finish
        
        # Safety buffer in hours. 
        # If slack drops below this, we risk missing the deadline.
        SAFE_BUFFER = 1.0
        
        # Force OD conditions:
        # 1. Low slack
        # 2. Very little work remaining (efficiency of spot diminishes vs risk of startup overhead)
        should_force_od = (slack < SAFE_BUFFER) or (remaining_work < 0.5)

        if should_force_od:
            # Choose a region for OD. Prefer keeping current region to avoid potential extra overhead 
            # (depending on simulator mechanics) or pick the cheapest spot region as a valid region proxy.
            target_region = self.current_region if (self.current_region in prices) else None
            if not target_region and prices:
                target_region = min(prices, key=prices.get)
            
            self.current_action = 'on_demand'
            self.current_region = target_region
            return 'on_demand', target_region

        # Spot Strategy
        if not prices:
            # No spot prices available, fallback to OD
            self.current_action = 'on_demand'
            return 'on_demand', self.current_region

        # Find best spot region
        sorted_regions = sorted(prices.items(), key=lambda x: x[1])
        best_region, best_price = sorted_regions[0]
        
        # Sticky Logic:
        # If we are already in a region, stay there unless the new best region is significantly cheaper.
        # Switching costs 'overhead' time.
        target_region = best_region
        if self.current_region in prices and self.current_action == 'spot':
            current_price = prices[self.current_region]
            # Heuristic: Stay if current price is within 15% of best price
            # This avoids thrashing between regions with similar prices
            if current_price <= best_price * 1.15:
                target_region = self.current_region
        
        # Sanity check: If spot price is very high (close to OD), just use OD for safety
        if prices[target_region] > self.od_price * 0.9:
            self.current_action = 'on_demand'
            self.current_region = target_region
            return 'on_demand', target_region

        self.current_action = 'spot'
        self.current_region = target_region
        return 'spot', target_region
