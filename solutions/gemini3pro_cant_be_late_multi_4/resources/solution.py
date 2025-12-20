import numpy as np

class Scheduler:
    def __init__(self, regions, deadline, task_duration, overhead, 
                 on_demand_price, spot_price, availability_probs, **kwargs):
        """
        Initialize the scheduler and pre-compute the optimal policy using Dynamic Programming.
        
        Args:
            regions (list): List of region names.
            deadline (int): Deadline in hours.
            task_duration (float): Task duration in hours.
            overhead (float): Restart overhead in hours (0.05 or 0.20).
            on_demand_price (float): Price of On-Demand instance.
            spot_price (float): Price of Spot instance.
            availability_probs (dict): Dictionary mapping region names to list of availability probabilities.
        """
        self.regions = regions
        self.r_map = {r: i for i, r in enumerate(regions)}
        self.n_regions = len(regions)
        self.deadline = int(deadline)
        self.task_duration = float(task_duration)
        self.overhead = float(overhead)
        self.p_od = float(on_demand_price)
        self.p_spot = float(spot_price)
        
        # Process probabilities into a (Deadline, N_Regions) matrix
        self.probs = np.zeros((self.deadline, self.n_regions))
        for r_idx, r_name in enumerate(regions):
            p_list = availability_probs.get(r_name, [])
            length = len(p_list)
            if length >= self.deadline:
                self.probs[:, r_idx] = p_list[:self.deadline]
            elif length > 0:
                self.probs[:length, r_idx] = p_list
                self.probs[length:, r_idx] = p_list[-1]
        
        # Discretization for DP
        # Using 0.05 as base unit since overheads are 0.05 or 0.20
        self.unit = 0.05
        self.units_per_hour = int(round(1.0 / self.unit))
        self.overhead_units = int(round(self.overhead / self.unit))
        self.max_work_units = int(np.ceil(self.task_duration / self.unit))
        
        # DP Value Table: V[time, work_remaining_idx, current_region_idx]
        # time: 0 to deadline
        # work: 0 to max_work_units
        # region: 0 to n_regions-1 (valid regions), n_regions (None/Start)
        self.V = np.full((self.deadline + 1, self.max_work_units + 1, self.n_regions + 1), np.inf)
        
        # Policy Table: Stores (action_type, target_region_idx)
        # action_type: 0 for Spot, 1 for On-Demand
        self.Policy = np.zeros((self.deadline, self.max_work_units + 1, self.n_regions + 1, 2), dtype=int)
        
        self._solve_dp()

    def _solve_dp(self):
        # Base case: Cost is 0 if no work remains
        self.V[:, 0, :] = 0.0
        
        # Work indices to compute (1 to max)
        w_indices = np.arange(1, self.max_work_units + 1)
        
        # Calculate next state work indices for stay vs switch
        # Staying: progress 1.0 hr
        w_next_stay = np.maximum(0, w_indices - self.units_per_hour)
        # Switching: progress 1.0 hr - overhead
        w_next_switch = np.maximum(0, w_indices - (self.units_per_hour - self.overhead_units))
        
        # Backward induction from deadline to 0
        for t in range(self.deadline - 1, -1, -1):
            p_t = self.probs[t] # Probabilities for current step (n_regions,)
            V_next = self.V[t+1]
            
            # Broadcast probabilities for vectorized operations
            p_bc = p_t[None, :] # Shape (1, n_regions)
            
            # Slices of V_next for all regions
            v_fail_all = V_next[w_indices, :self.n_regions]             # If spot fails: progress 0, loc k
            v_succ_stay_all = V_next[w_next_stay, :self.n_regions]      # If spot succeeds & stay: progress 1.0
            v_succ_switch_all = V_next[w_next_switch, :self.n_regions]  # If spot succeeds & switch: progress 1.0-overhead
            
            # 1. Compute costs for targeting each region k with Spot
            # spot_cost_stay[k]: cost targeting k given we are in k
            # spot_cost_switch[k]: cost targeting k given we are NOT in k
            spot_cost_stay = (self.p_spot + p_bc * v_succ_stay_all + (1 - p_bc) * v_fail_all).T
            spot_cost_switch = (self.p_spot + p_bc * v_succ_switch_all + (1 - p_bc) * v_fail_all).T
            
            # 2. Compute costs for targeting each region k with On-Demand
            od_cost_stay = (self.p_od + v_succ_stay_all).T
            od_cost_switch = (self.p_od + v_succ_switch_all).T
            
            # 3. Determine best action for each possible current region r
            
            # Case A: Currently in a valid region r
            for r in range(self.n_regions):
                # Construct specific cost options from r
                c_spot = spot_cost_switch.copy()
                c_spot[r] = spot_cost_stay[r] # If target is r, use stay cost
                
                c_od = od_cost_switch.copy()
                c_od[r] = od_cost_stay[r]
                
                # Find best target for Spot and OD
                best_spot_val = np.min(c_spot, axis=0)
                best_spot_idx = np.argmin(c_spot, axis=0)
                
                best_od_val = np.min(c_od, axis=0)
                best_od_idx = np.argmin(c_od, axis=0)
                
                # Choose between Spot and OD
                use_od = best_od_val < best_spot_val
                
                self.V[t, w_indices, r] = np.where(use_od, best_od_val, best_spot_val)
                self.Policy[t, w_indices, r, 0] = np.where(use_od, 1, 0)
                self.Policy[t, w_indices, r, 1] = np.where(use_od, best_od_idx, best_spot_idx)
                
            # Case B: Currently in None/Start state (index n_regions)
            # All targets are switches
            best_spot_val = np.min(spot_cost_switch, axis=0)
            best_spot_idx = np.argmin(spot_cost_switch, axis=0)
            
            best_od_val = np.min(od_cost_switch, axis=0)
            best_od_idx = np.argmin(od_cost_switch, axis=0)
            
            use_od = best_od_val < best_spot_val
            
            self.V[t, w_indices, self.n_regions] = np.where(use_od, best_od_val, best_spot_val)
            self.Policy[t, w_indices, self.n_regions, 0] = np.where(use_od, 1, 0)
            self.Policy[t, w_indices, self.n_regions, 1] = np.where(use_od, best_od_idx, best_spot_idx)

    def step(self, t, work_done, current_region):
        """
        Get the optimal action for the current state.
        
        Args:
            t (int): Current time step (hour).
            work_done (float): Total work completed so far.
            current_region (str or None): Name of the current region.
            
        Returns:
            tuple: (action_type, target_region)
                   action_type is 'spot' or 'on_demand'
                   target_region is the name of the region
        """
        t = int(t)
        if t >= self.deadline:
            return None
            
        work_remaining = max(0.0, self.task_duration - work_done)
        if work_remaining <= 1e-6:
            # If work is done, stay in current region or default to 0 (spot) to finish
            r = current_region if current_region is not None else self.regions[0]
            return 'spot', r
            
        # Map state to indices
        w_idx = int(np.ceil(work_remaining / self.unit))
        if w_idx > self.max_work_units: w_idx = self.max_work_units
        
        if current_region is None:
            r_idx = self.n_regions
        else:
            r_idx = self.r_map.get(current_region, self.n_regions)
            
        # Lookup policy
        action_code, target_idx = self.Policy[t, w_idx, r_idx]
        target_region = self.regions[target_idx]
        action_type = 'on_demand' if action_code == 1 else 'spot'
        
        return action_type, target_region
