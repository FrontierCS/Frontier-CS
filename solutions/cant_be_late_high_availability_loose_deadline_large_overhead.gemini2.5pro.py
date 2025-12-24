import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "risk_aware_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        # --- Hyperparameters ---
        # EMA smoothing factor for probability estimates. Lower is smoother.
        self.ema_alpha = 0.001
        # Safety multiplier for risk calculation. >1 makes the agent more
        # risk-averse, switching to on-demand earlier.
        self.safety_multiplier = 1.8
        # Initial guess for P(preemption | spot was up). Corresponds to an avg.
        # uptime of 1/0.04 = 25 steps before online estimation takes over.
        self.initial_p_preempt = 0.04
        # Initial guess for P(recovery | spot was down). Corresponds to an avg.
        # downtime of 1/0.10 = 10 steps.
        # These initial guesses imply a starting spot availability of ~71%.
        self.initial_p_recover = 0.10

        # --- State for Online Estimation ---
        self.p_preempt = self.initial_p_preempt
        self.p_recover = self.initial_p_recover
        
        self.n11 = 0  # Count of up -> up transitions
        self.n10 = 0  # Count of up -> down (preemption)
        self.n01 = 0  # Count of down -> up (recovery)
        self.n00 = 0  # Count of down -> down
        
        self.last_has_spot = None

        return self

    def _update_spot_stats(self, has_spot: bool):
        """Updates the transition probability estimates based on the latest observation."""
        if self.last_has_spot is None:
            self.last_has_spot = has_spot
            return

        # Update transition counts based on the (last_state, current_state) pair
        if self.last_has_spot and has_spot:
            self.n11 += 1
        elif self.last_has_spot and not has_spot:
            self.n10 += 1
        elif not self.last_has_spot and has_spot:
            self.n01 += 1
        else: # not self.last_has_spot and not has_spot
            self.n00 += 1
        
        # Update probability estimates using EMA for stability
        if (self.n10 + self.n11) > 0:
            current_p_preempt = self.n10 / (self.n10 + self.n11)
            self.p_preempt = (self.ema_alpha * current_p_preempt +
                              (1 - self.ema_alpha) * self.p_preempt)

        if (self.n01 + self.n00) > 0:
            current_p_recover = self.n01 / (self.n01 + self.n00)
            self.p_recover = (self.ema_alpha * current_p_recover +
                              (1 - self.ema_alpha) * self.p_recover)
        
        self.last_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_stats(has_spot)

        # 1. Calculate current state
        total_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - total_done
        
        if work_remaining <= 1e-6:
            return ClusterType.NONE # Job is done

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # 2. Handle the "Point of No Return"
        # If remaining work is more than remaining time, we must use On-Demand.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # 3. Dynamic Risk Assessment
        # Estimate the total "time cost" of a spot-first strategy for the rest of the job.
        
        # Cost from future restarts:
        num_compute_steps = work_remaining / self.env.gap_seconds
        expected_preemptions = num_compute_steps * self.p_preempt
        cost_from_restarts = expected_preemptions * self.restart_overhead

        # Cost from future downtime:
        if self.p_recover > 1e-9:
            cost_from_downtime = work_remaining * (self.p_preempt / self.p_recover)
        else:
            cost_from_downtime = float('inf')

        total_risk_estimate = (cost_from_restarts + cost_from_downtime) * self.safety_multiplier
        
        # 4. Make a Decision
        # Compare available time buffer (slack) with the estimated risk.
        current_slack = time_to_deadline - work_remaining

        if current_slack < total_risk_estimate:
            # Slack is too low to safely absorb potential spot disruptions.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack, so prioritize cost savings.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        # Required by the evaluator for instantiation.
        args, _ = parser.parse_known_args()
        return cls(args)
