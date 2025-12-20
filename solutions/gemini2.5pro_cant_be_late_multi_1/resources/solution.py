import collections
import math

class MultiRegionSpotScheduler:
    """
    A scheduler for multi-region spot instances to complete a task with a deadline at minimum cost.
    This implementation uses dynamic programming to find the optimal schedule.
    """

    def schedule(self, num_regions, num_timesteps, task_duration, deadline,
                 restart_overhead, on_demand_price, spot_prices, spot_availability):
        """
        Calculates the optimal schedule using dynamic programming.

        The DP state is defined as dp[t][(w, r)], representing the minimum cost to achieve
        'w' units of work by time 't', with the last instance running in region 'r'.
        Work 'w' is scaled to an integer to avoid floating-point precision issues.
        The state space is pruned at each time step to keep only the Pareto-optimal states,
        i.e., for a given region, we only keep states (w, cost) that are not dominated by
        any other state (w', cost') where w' >= w and cost' <= cost.

        Args:
            num_regions (int): The number of available regions.
            num_timesteps (int): The number of time steps in the traces.
            task_duration (float): The total amount of work to be completed.
            deadline (int): The time by which the task must be completed.
            restart_overhead (float): The time lost when starting a new instance.
            on_demand_price (dict): A map from region_id to on-demand price.
            spot_prices (dict): A map from region_id to a list of spot prices over time.
            spot_availability (dict): A map from region_id to a list of spot availability flags.

        Returns:
            list: A list of tuples representing the schedule, where each tuple is
                  (instance_type, region_id). 'idle' is used for no-op.
        """
        
        # 1. Constants and Scaling
        # Use a scaling factor to convert float work units to integers, avoiding precision issues.
        # The smallest unit of overhead is 0.05, which is 1/20. So 20 is a good scale.
        W_SCALE = 20
        TASK_DUR_INT = int(task_duration * W_SCALE)
        WORK_CONTINUE = int(1.0 * W_SCALE)
        WORK_RESTART = int((1.0 - restart_overhead) * W_SCALE)

        # 2. DP Table Initialization
        # dp[t] maps state (work_int, region_id) to its minimum cost.
        # region_id = -1 represents an idle state.
        dp = [collections.defaultdict(lambda: float('inf')) for _ in range(deadline + 1)]
        # parent[t] stores back-pointers to reconstruct the path.
        # parent[t][(w, r)] = (decision_at_t-1, prev_w, prev_r)
        parent = [{} for _ in range(deadline + 1)]
        
        # Initial state: at time 0, 0 work is done, cost is 0, system is idle.
        dp[0][(0, -1)] = 0.0

        # 3. Main DP Loop
        for t in range(deadline):
            if not dp[t]:
                continue
            
            # --- Transitions from time t to t+1 ---
            for state, cost in dp[t].items():
                prev_w_int, prev_r = state

                # Decision: Be idle for the current hour 't'
                idle_w, idle_r = prev_w_int, -1
                idle_cost = cost
                if idle_cost < dp[t+1][(idle_w, idle_r)]:
                    dp[t+1][(idle_w, idle_r)] = idle_cost
                    parent[t+1][(idle_w, idle_r)] = (('idle', -1), prev_w_int, prev_r)

                # If task is already completed, no need to run more instances.
                if prev_w_int >= TASK_DUR_INT:
                    continue
                
                # Decision: Run an instance in a region for hour 't'
                for j in range(num_regions):
                    is_restart = (j != prev_r)
                    work_this_hour_int = WORK_RESTART if is_restart else WORK_CONTINUE

                    # a) On-Demand Instance
                    od_w = prev_w_int + work_this_hour_int
                    od_r = j
                    od_cost = cost + on_demand_price[j]
                    if od_cost < dp[t+1][(od_w, od_r)]:
                        dp[t+1][(od_w, od_r)] = od_cost
                        parent[t+1][(od_w, od_r)] = (('on-demand', j), prev_w_int, prev_r)
                    
                    # b) Spot Instance
                    spot_cost = cost + spot_prices[j][t]
                    if spot_availability[j][t] == 1: # Spot available
                        spot_w = prev_w_int + work_this_hour_int
                        spot_r = j
                        if spot_cost < dp[t+1][(spot_w, spot_r)]:
                            dp[t+1][(spot_w, spot_r)] = spot_cost
                            parent[t+1][(spot_w, spot_r)] = (('spot', j), prev_w_int, prev_r)
                    else: # Spot preempted
                        spot_w = prev_w_int
                        spot_r = -1 # State becomes idle as instance is terminated
                        if spot_cost < dp[t+1][(spot_w, spot_r)]:
                            dp[t+1][(spot_w, spot_r)] = spot_cost
                            parent[t+1][(spot_w, spot_r)] = (('spot', j), prev_w_int, prev_r)
            
            # --- Pruning Step for dp[t+1] ---
            # Keep only non-dominated states (Pareto frontier) to manage state space size.
            if not dp[t+1]:
                continue
            
            pruned_dp_t_plus_1 = collections.defaultdict(lambda: float('inf'))
            pruned_parent_t_plus_1 = {}
            
            states_by_region = collections.defaultdict(list)
            for state, cost in dp[t+1].items():
                w, r = state
                states_by_region[r].append((w, cost))

            for r, state_list in states_by_region.items():
                state_list.sort(key=lambda x: (-x[0], x[1])) # Sort by work desc, cost asc
                
                min_cost_on_frontier = float('inf')
                for w, cost in state_list:
                    if cost < min_cost_on_frontier:
                        pruned_dp_t_plus_1[(w, r)] = cost
                        pruned_parent_t_plus_1[(w, r)] = parent[t+1][(w, r)]
                        min_cost_on_frontier = cost
            
            dp[t+1] = pruned_dp_t_plus_1
            parent[t+1] = pruned_parent_t_plus_1

        # 4. Find Best Final State
        min_total_cost = float('inf')
        best_final_t = -1
        best_final_state_key = None

        for t in range(1, deadline + 1):
            for state, cost in dp[t].items():
                w_int, _ = state
                if w_int >= TASK_DUR_INT:
                    if cost < min_total_cost:
                        min_total_cost = cost
                        best_final_t = t
                        best_final_state_key = state

        # 5. Backtrack to Reconstruct Schedule
        if best_final_state_key is None:
            # Fallback: if no solution is found, provide a best-effort schedule.
            cheapest_region = min(range(num_regions), key=lambda r: on_demand_price[r])
            return [('on-demand', cheapest_region)] * num_timesteps
        
        schedule = [('idle', -1)] * deadline
        curr_t = best_final_t
        curr_key = best_final_state_key

        while curr_t > 0:
            decision, prev_w_int, prev_r = parent[curr_t][curr_key]
            schedule[curr_t - 1] = decision
            curr_key = (prev_w_int, prev_r)
            curr_t -= 1
        
        # Ensure schedule has length num_timesteps
        if len(schedule) < num_timesteps:
            schedule.extend([('idle', -1)] * (num_timesteps - len(schedule)))

        return schedule[:num_timesteps]
