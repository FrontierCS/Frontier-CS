import math
import random

class Scheduler:
    def __init__(self, variant, overhead, deadline, task_duration, regions, **kwargs):
        """
        Initialize the scheduler with problem constraints.
        
        Args:
            variant (str): The specific problem variant string.
            overhead (float): Restart overhead in hours (e.g., 0.05 or 0.20).
            deadline (float): Absolute deadline in hours (e.g., 36 or 48).
            task_duration (float): Total work required in hours (24).
            regions (list): List of available region names.
        """
        self.variant = variant
        self.overhead = overhead
        self.deadline = deadline
        self.task_duration = task_duration
        self.regions = regions
        
        # Pricing constants (estimated from problem description)
        self.OD_PRICE = 3.06
        self.SPOT_PRICE_AVG = 0.97
        
        # State tracking
        self.use_od_latch = False

    def schedule(self, current_time, remaining_work, region_status, current_context):
        """
        Decide the scheduling action for the current timestep.

        Args:
            current_time (float): Current time in hours.
            remaining_work (float): Remaining work to complete in hours.
            region_status (dict): Dictionary mapping region names to status dicts.
                                  Example: {'us-east-1': {'available': True, 'spot_price': 0.5}}
            current_context (dict): Dictionary with current status.
                                    Example: {'region': 'us-east-1', 'instance_type': 'spot', 'is_running': True}

        Returns:
            dict: Action dictionary {'region': str, 'instance_type': 'spot'|'on_demand'}
        """
        
        # 1. Calculate Constraints
        time_left = self.deadline - current_time
        
        # Determine current state
        current_region = current_context.get('region')
        is_running = current_context.get('is_running', False)
        current_type = current_context.get('instance_type', 'spot')
        
        # Effective slack calculation
        # If we are NOT running, we must pay overhead to start/restart
        penalty = 0.0 if is_running else self.overhead
        slack = time_left - (remaining_work + penalty)
        
        # 2. Determine Strategy (Safety vs Cost)
        
        # Panic Threshold: minimal buffer to safely handle an interruption loop
        # We need at least enough slack to absorb a few restarts if we stick with Spot.
        # If slack drops below ~4x overhead (approx 1 hour for large overhead), switch to OD.
        panic_threshold = max(self.overhead * 5.0, 1.5)
        
        if slack < panic_threshold:
            self.use_od_latch = True
            
        # 3. Analyze Candidates
        candidates = []
        for r in self.regions:
            if r not in region_status:
                continue
            
            info = region_status[r]
            # Handle potential missing keys gracefully
            s_price = info.get('spot_price', float('inf'))
            is_avail = info.get('available', True)
            
            # Sanity check on price
            if s_price is None or s_price > self.OD_PRICE:
                is_avail = False
                s_price = float('inf')
                
            candidates.append({
                'region': r,
                'spot_price': s_price,
                'available': is_avail
            })
            
        # 4. Select Action
        
        # STRATEGY: ON-DEMAND (Safety)
        if self.use_od_latch:
            # If already running OD, stay put
            if is_running and current_type == 'on_demand':
                return {'region': current_region, 'instance_type': 'on_demand'}
            
            # If running Spot, we want to upgrade to OD.
            # CRITICAL: If slack < overhead, switching kills the job. 
            # We must gamble on the current spot instance finishing.
            if is_running and current_type == 'spot':
                if slack < self.overhead:
                    return {'region': current_region, 'instance_type': 'spot'}
            
            # Otherwise, pick best region for OD.
            # Just pick the first valid region (OD assumed always available).
            best_r = candidates[0]['region']
            return {'region': best_r, 'instance_type': 'on_demand'}

        # STRATEGY: SPOT (Cost)
        
        # Sticky policy: If currently running Spot and region is healthy, stay.
        if is_running and current_type == 'spot' and current_region:
            curr_stats = next((c for c in candidates if c['region'] == current_region), None)
            if curr_stats and curr_stats['available']:
                return {'region': current_region, 'instance_type': 'spot'}

        # If not running or current region failed, pick cheapest available Spot
        available_spots = [c for c in candidates if c['available']]
        
        if not available_spots:
            # Fallback to OD if no spot is available
            self.use_od_latch = True
            return {'region': candidates[0]['region'], 'instance_type': 'on_demand'}
            
        # Sort by price
        available_spots.sort(key=lambda x: x['spot_price'])
        best_r = available_spots[0]['region']
        
        return {'region': best_r, 'instance_type': 'spot'}
