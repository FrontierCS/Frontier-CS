from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        self._cached_total_work_done = 0.0
        self._cached_task_done_len = 0
        return self

    def _get_total_work_done(self) -> float:
        """
        Calculates the total work done so far, using a cache to avoid
        re-summing the entire list of completed work segments at every step.
        """
        if self._cached_task_done_len < len(self.task_done_time):
            new_segments = self.task_done_time[self._cached_task_done_len:]
            new_work = sum(end - start for start, end in new_segments)
            self._cached_total_work_done += new_work
            self._cached_task_done_len = len(self.task_done_time)
        return self._cached_total_work_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        total_work_done = self._get_total_work_done()
        work_remaining = self.task_duration - total_work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        effective_work_rem = work_remaining + self.env.restart_overhead_pending
        
        effective_slack = time_to_deadline - effective_work_rem

        # This is the Point of No Return (PNR) threshold. It represents the
        # minimum slack required to survive a worst-case scenario (a spot
        # preemption at the next step) and still be able to finish by the
        # deadline using on-demand instances.
        # The logic is:
        # effective_slack >= required_buffer_for_preemption
        # effective_slack >= (restart_overhead - current_pending_overhead + gap_seconds)
        pnr_threshold = (self.restart_overhead -
                         self.env.restart_overhead_pending +
                         self.env.gap_seconds)
        
        if effective_slack < pnr_threshold:
            # We are in the "critical zone". The slack is insufficient to absorb
            # another preemption. We must use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND
        else:
            # We are in the "safe zone", with enough slack to tolerate at least
            # one more preemption.
            if has_spot:
                # Spot is available, so we use the cheaper option.
                return ClusterType.SPOT
            else:
                # Spot is not available. Since we have sufficient slack, we can
                # afford to wait for it to become available again, saving costs.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        For evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)