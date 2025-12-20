import math
import random

class Scheduler:
    def __init__(self, variant: str, regions: list, **kwargs):
        """
        Initialize the scheduler with problem constraints based on the variant.
        """
        self.variant = variant
        self.regions = regions
        self.task_duration = 24.0
        self.on_demand_price = 3.06
        
        # Parse variant configuration
        # Deadline: tight=36h, loose=48h
        self.deadline = 36.0 if "tight_deadline" in variant else 48.0
        
        # Overhead: small=0.05h, large=0.20h
        self.overhead = 0.20 if "large_overhead" in variant else 0.05
        
        # Availability hint: prefer east coast if high_availability (proxy for stability)
        self.prefer_east = "high_availability" in variant
        
        # Heuristic parameters
        # Panic threshold: time buffer to force switch to On-Demand
        self.panic_threshold = 0.1 
        # Stickiness: prevent switching for minor price gains (avoid overhead risk)
        self.stickiness_factor = 0.85

    def schedule(self, observation: dict) -> dict:
        """
        Decide scheduling action based on current observation.
        
        Args:
            observation: Dict containing 'time', 'progress', 'running', 
                         'current_region', and 'region_status'.
                         
        Returns:
            Dict with 'action' ('run'/'stop'), 'region', and 'type' ('spot'/'on_demand').
        """
        current_time = observation.get("time", 0.0)
        progress = observation.get("progress", 0.0)
        is_running = observation.get("running", False)
        current_region = observation.get("current_region", None)
        region_status = observation.get("region_status", {})
        
        remaining_work = self.task_duration - progress
        
        # Terminal condition check
        if remaining_work <= 0:
            return {"action": "stop"}

        # --- SAFETY CHECK (Deadline Constraint) ---
        # Calculate time required to finish if we switch to On-Demand NOW.
        # We add overhead because switching to OD (or starting it) typically incurs restart cost.
        # Conservative estimate: Assume we always pay overhead to switch/start OD.
        time_to_finish_od = remaining_work + self.overhead
        
        # Slack = Time Remaining - Time Required for Safe OD Run
        slack = (self.deadline - current_time) - time_to_finish_od
        
        # If slack is critically low, force On-Demand to guarantee completion.
        if slack < self.panic_threshold:
            # Stick to current region if possible to potentially minimize cross-region overheads
            target = current_region if (is_running and current_region in self.regions) else self.regions[0]
            return {
                "action": "run", 
                "region": target, 
                "type": "on_demand"
            }

        # --- COST OPTIMIZATION (Spot Strategy) ---
        candidates = []
        for r in self.regions:
            info = region_status.get(r, {})
            # Support various simulator data formats
            status = info.get("status", "available")
            price = info.get("spot_price", 10.0) # Default high price if missing
            
            if status == "available":
                # Adjust effective price based on availability hints
                # This encourages using more stable regions (East) when availability is high
                # and penalizes West regions when availability is low, or vice versa based on variant hints.
                effective_price = price
                if self.prefer_east:
                    if "east" in r:
                        effective_price *= 0.95  # Bias towards East
                    elif "west" in r:
                        effective_price *= 1.05  # Bias against West
                
                candidates.append((r, price, effective_price))
        
        # If no spot instances are available, fallback to On-Demand
        if not candidates:
            target = current_region if (is_running and current_region in self.regions) else self.regions[0]
            return {"action": "run", "region": target, "type": "on_demand"}
            
        # Sort candidates by the effective (biased) price
        candidates.sort(key=lambda x: x[2])
        best_region = candidates[0][0]
        best_price = candidates[0][1]
        
        # --- HYSTERESIS (Inertia) ---
        # Don't switch regions unless the savings are significant.
        # Switching incurs 'overhead' time loss, which effectively costs money and safety.
        target_region = best_region
        
        if is_running and current_region:
            # Check if current region is in candidates (still available)
            curr_cand = next((c for c in candidates if c[0] == current_region), None)
            
            if curr_cand:
                curr_price = curr_cand[1]
                # If we are currently running, only switch if:
                # Best_Price < Current_Price * Stickiness (e.g., 15% cheaper)
                if best_price > curr_price * self.stickiness_factor:
                    target_region = current_region
            else:
                # Current region is interrupted or unavailable -> Must switch
                target_region = best_region

        return {
            "action": "run",
            "region": target_region,
            "type": "spot"
        }
