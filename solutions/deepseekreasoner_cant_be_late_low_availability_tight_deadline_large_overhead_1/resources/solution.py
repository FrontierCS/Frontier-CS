import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = None
        self.initialized = False
        self.spot_available_history = []
        self.use_spot_threshold = 0.7
        self.last_spot_status = True
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        try:
            with open(spec_path, 'r') as f:
                # Parse any configuration if provided
                pass
        except:
            pass
        return self
    
    def _initialize_state(self):
        """Initialize remaining work based on completed segments"""
        if self.initialized:
            return
            
        # Calculate remaining work
        total_done = 0
        for start, end in self.task_done_time:
            total_done += end - start
        
        self.remaining_work = self.task_duration - total_done
        self.initialized = True
    
    def _update_remaining_work(self):
        """Update remaining work based on current state"""
        if not self.initialized:
            self._initialize_state()
            return
            
        # If we're currently running and not in restart overhead, subtract work done
        if self.env.cluster_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
            # Check if we're in restart overhead (simplified check)
            # In practice, we'd need to track restart state more precisely
            self.remaining_work = max(0, self.remaining_work - self.env.gap_seconds)
    
    def _calculate_risk_level(self, has_spot: bool) -> float:
        """Calculate risk level based on time remaining and work left"""
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        if self.remaining_work <= 0:
            return 0.0  # Work is done, no risk
        
        # Calculate minimum time needed with on-demand (no restart overhead)
        min_time_needed = self.remaining_work
        
        # Add conservative restart overhead estimate
        # Assuming we might need 1 restart if using spot
        if self.last_spot_status and not has_spot:
            # Spot just became unavailable, higher risk
            min_time_needed += self.restart_overhead
        
        # Calculate safety margin
        safety_margin = time_remaining - min_time_needed
        
        # Normalize risk (0 = safe, 1 = critical)
        if safety_margin <= 0:
            return 1.0
        elif safety_margin >= 4 * 3600:  # 4 hours of slack
            return 0.0
        else:
            return 1.0 - (safety_margin / (4 * 3600))
    
    def _should_use_spot(self, has_spot: bool, risk_level: float) -> bool:
        """Decide whether to use spot based on availability and risk"""
        if not has_spot:
            return False
            
        # Use spot if risk is below threshold and spot is available
        return risk_level < self.use_spot_threshold
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize state on first call
        if not self.initialized:
            self._initialize_state()
        
        # Track spot availability history (for adaptive threshold)
        self.spot_available_history.append(has_spot)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
        
        # Update remaining work
        self._update_remaining_work()
        
        # Calculate current risk level
        risk_level = self._calculate_risk_level(has_spot)
        
        # Adaptive threshold based on spot availability history
        if len(self.spot_available_history) >= 50:
            spot_availability_rate = sum(self.spot_available_history) / len(self.spot_available_history)
            # Lower threshold when spot is less available
            if spot_availability_rate < 0.2:
                self.use_spot_threshold = 0.3
            elif spot_availability_rate < 0.4:
                self.use_spot_threshold = 0.5
            else:
                self.use_spot_threshold = 0.7
        
        # Strategy decision
        if self._should_use_spot(has_spot, risk_level):
            # Use spot when available and risk is acceptable
            decision = ClusterType.SPOT
        elif risk_level >= 0.9:
            # Critical risk - use on-demand
            decision = ClusterType.ON_DEMAND
        elif risk_level >= 0.7 and has_spot:
            # Moderate risk but spot available - conservative approach
            decision = ClusterType.SPOT
        elif risk_level >= 0.5:
            # Medium risk - use on-demand to ensure progress
            decision = ClusterType.ON_DEMAND
        elif not has_spot and risk_level < 0.3:
            # No spot available but low risk - wait for spot
            decision = ClusterType.NONE
        else:
            # Default to on-demand for safety
            decision = ClusterType.ON_DEMAND
        
        # Ensure we don't return SPOT when not available
        if decision == ClusterType.SPOT and not has_spot:
            # Fall back to on-demand if we need to make progress
            if risk_level > 0.5:
                decision = ClusterType.ON_DEMAND
            else:
                decision = ClusterType.NONE
        
        # Store current spot status for next decision
        self.last_spot_status = has_spot
        
        return decision
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
