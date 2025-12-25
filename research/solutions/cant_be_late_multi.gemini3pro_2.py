import numpy as np
import math

class Scheduler:
    def __init__(self, history, config):
        """
        Multi-region scheduler using Dynamic Programming.
        """
        self.regions = config.get('regions', [])
        if not self.regions:
            # Fallback if regions not in config, though they should be
            self.regions = ['us-east-1', 'us-west-1', 'us-west-2', 'us-east-2', 
                          'eu-central-1', 'eu-west-1', 'ap-northeast-1', 'ap-southeast-1', 'sa-east-1']
            
        self.deadline = float(config.get('deadline', 48.0))
        self.duration = float(config.get('duration', 24.0))
        self.overhead = float(config.get('overhead', 0.05))
        self.od_price = float(config.get('on_demand_price', 3.06))
        
        # Parse spot prices, default to 0.97 if missing
        self.spot_prices = {}
        provided_prices = config.get('spot_prices', {})
        for r in self.regions:
            self.spot_prices[r] = float(provided_prices.get(r, 0.97))
            
        self.r_map = {r: i for i, r in enumerate(self.regions)}
        self.n_regions = len(self.regions)
        
        # DP parameters
        # dt = 0.1h (6 mins) balances precision and performance
        self.dt = 0.1 
        self.n_time = int(math.ceil(self.deadline / self.dt)) + 5
        self.n_prog = int(math.ceil(self.duration / self.dt)) + 5
        
        # Estimate availability from history
        self.avail_probs = self._process_history(history)
        
        # DP Table: V[time_idx, progress_idx, current_region_idx]
        # Region index: 0..N-1 are regions, N is None (no active region/start)
        self.V = np.full((self.n_time, self.n_prog, self.n_regions + 1), np.inf, dtype=np.float32)
        
        # Policy: Stores action index. -1 for OD, 0..N-1 for Spot Region
        self.policy = np.full((self.n_time, self.n_prog, self.n_regions + 1), -1, dtype=np.int8)
        
        self._solve_dp()

    def _process_history(self, history):
        # Estimates availability probability P(avail | region, time_of_day)
        steps_per_day = int(24.0 / self.dt)
        # Default prior: 95% availability
        probs = np.full((self.n_regions, steps_per_day), 0.95)
        
        if not history:
            return probs
            
        try:
            # Handle history if it's a dict mapping region -> data
            for i, r in enumerate(self.regions):
                if r in history:
                    data = history[r]
                    # Attempt to calculate mean availability
                    # Robust handling for list, numpy array, or pandas series
                    if hasattr(data, 'mean'):
                        val = float(data.mean())
                        probs[i, :] = val
                    elif isinstance(data, list) and len(data) > 0:
                        val = sum(data) / len(data)
                        probs[i, :] = val
        except:
            # Fallback to default if parsing fails
            pass
            
        return probs

    def _solve_dp(self):
        NONE_IDX = self.n_regions
        
        # Base case: if progress >= duration, cost is 0
        self.V[:, -1, :] = 0.0
        
        # Precompute costs
        spot_costs = np.array([self.spot_prices[r] for r in self.regions]) * self.dt
        od_cost = self.od_price * self.dt
        
        # Overhead handling
        # Number of steps consumed by overhead
        overhead_steps = int(math.ceil(self.overhead / self.dt))
        # Cost incurred during overhead (approximate as rate * time)
        overhead_cost_vals = spot_costs * (self.overhead / self.dt)
        
        steps_per_day = self.avail_probs.shape[1]
        
        # Backward induction
        for t in range(self.n_time - 2, -1, -1):
            tod = t % steps_per_day
            if tod >= steps_per_day: tod = 0
            
            p_avails = self.avail_probs[:, int(tod)]
            V_next = self.V[t+1]
            
            # --- Option 1: On-Demand ---
            # Reliable, 1 step progress. Assuming OD effectively resets region context to safe state (None)
            # or works from any state. We model result state as None to simplify.
            cost_od = np.full(self.n_prog, np.inf, dtype=np.float32)
            cost_od[:-1] = od_cost + V_next[1:, NONE_IDX]
            cost_od[-1] = 0.0
            
            # --- Option 2: Spot ---
            
            # Sub-case A: STAY in region i (r_curr == i)
            # Cost = step_cost + P_avail * V(t+1, p+1, i) + (1-P) * V(t+1, p, None)
            val_stay = np.zeros((self.n_regions, self.n_prog), dtype=np.float32)
            
            # Fail term (interruption -> None state, no progress)
            v_fail = V_next[:, NONE_IDX]
            
            for i in range(self.n_regions):
                pa = p_avails[i]
                # Success term (progress +1)
                v_succ = np.zeros(self.n_prog, dtype=np.float32)
                v_succ[:-1] = V_next[1:, i]
                
                val_stay[i] = spot_costs[i] + pa * v_succ + (1 - pa) * v_fail

            # Sub-case B: SWITCH to region i (r_curr != i)
            # Cost = overhead_cost + V(t+overhead, p, i) [Approximate]
            # We look ahead by overhead_steps. Progress p stays same during overhead.
            t_fut = min(self.n_time - 1, t + overhead_steps)
            V_fut = self.V[t_fut]
            
            val_switch = np.zeros((self.n_regions, self.n_prog), dtype=np.float32)
            for i in range(self.n_regions):
                pa = p_avails[i]
                # Success term after overhead (p same)
                v_succ_sw = V_fut[:, i]
                # Fail term (interrupted during or immediately after overhead)
                v_fail_sw = V_next[:, NONE_IDX] 
                
                # Check if overhead pushes past deadline
                if t_fut >= self.n_time - 1:
                    val_switch[i] = np.inf
                else:
                    val_switch[i] = overhead_cost_vals[i] + pa * v_succ_sw + (1 - pa) * v_fail_sw

            # --- Select Best Action ---
            for r_curr in range(self.n_regions + 1):
                best_v = cost_od.copy()
                best_a = np.full(self.n_prog, -1, dtype=np.int8)
                
                for r_target in range(self.n_regions):
                    if r_curr == r_target:
                        vals = val_stay[r_target]
                    else:
                        vals = val_switch[r_target]
                    
                    mask = vals < best_v
                    best_v[mask] = vals[mask]
                    best_a[mask] = r_target
                
                self.V[t, :, r_curr] = best_v
                self.policy[t, :, r_curr] = best_a

    def step(self, current_time, current_progress, current_region, *args, **kwargs):
        """
        Determine the next action based on current state.
        """
        # Map state to indices
        t_idx = int(round(current_time / self.dt))
        p_idx = int(round(current_progress / self.dt))
        
        # Bounds check
        t_idx = min(max(0, t_idx), self.n_time - 1)
        p_idx = min(max(0, p_idx), self.n_prog - 1)
        
        if current_region is None or current_region not in self.r_map:
            r_idx = self.n_regions
        else:
            r_idx = self.r_map[current_region]
            
        # Lookup policy
        action_idx = self.policy[t_idx, p_idx, r_idx]
        
        if action_idx == -1:
            return {'action': 'on_demand', 'region': None}
        else:
            region_name = self.regions[action_idx]
            return {'action': 'spot', 'region': region_name}
