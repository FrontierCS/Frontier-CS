from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize strategy parameters
        self.commit_to_on_demand = False
        # Safety multiplier on restart overhead to be conservative
        self.overhead_safety_mult = 2.0
        return self

    def _get_progress(self) -> float:
        """Estimate how much of the task has been completed (in seconds)."""
        try:
            segments = self.task_done_time
        except AttributeError:
            return 0.0

        if not segments:
            return 0.0

        try:
            last = segments[-1]
        except Exception:
            return 0.0

        total = 0.0
        # Case 1: list of (start, end) segments
        if isinstance(last, (list, tuple)) and len(last) == 2:
            for seg in segments:
                if not isinstance(seg, (list, tuple)) or len(seg) != 2:
                    continue
                s, e = seg
                try:
                    s_f = float(s)
                    e_f = float(e)
                except Exception:
                    continue
                if e_f > s_f:
                    total += e_f - s_f
        else:
            # Case 2: assume cumulative progress markers; take the last
            try:
                total = float(last)
            except Exception:
                total = 0.0

        if total < 0.0:
            total = 0.0
        try:
            duration = float(self.task_duration)
            if total > duration:
                total = duration
        except Exception:
            pass
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure attributes exist if solve() was not called
        if not hasattr(self, "commit_to_on_demand"):
            self.commit_to_on_demand = False
        if not hasattr(self, "overhead_safety_mult"):
            self.overhead_safety_mult = 2.0

        env = self.env
        t = float(env.elapsed_seconds)
        gap = float(env.gap_seconds)
        total_duration = float(self.task_duration)
        deadline = float(self.deadline)

        # Compute how much work is done
        progress = self._get_progress()
        remaining_work = max(0.0, total_duration - progress)

        # If task is already complete, stop using compute resources
        if remaining_work <= 0.0:
            self.commit_to_on_demand = True
            return ClusterType.NONE

        # Time remaining until deadline
        time_left = max(0.0, deadline - t)
        if time_left <= 0.0:
            # Already past deadline; nothing sensible to do but avoid cost
            self.commit_to_on_demand = True
            return ClusterType.NONE

        # Conservative estimate of time needed if we switch to on-demand now
        overhead_fudge = self.overhead_safety_mult * float(self.restart_overhead)
        od_need = remaining_work + overhead_fudge

        # Decide whether to irrevocably commit to on-demand
        if not self.commit_to_on_demand:
            slack = time_left - od_need
            # If slack is at most one step, don't risk waiting further
            if slack <= gap:
                self.commit_to_on_demand = True

        # If committed, always use on-demand to guarantee completion
        if self.commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet committed: we can still exploit spot to save cost
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable and we haven't committed yet.
        # Decide between idling and opportunistic on-demand.
        slack = time_left - od_need
        # If we have more than ~2 steps of slack, we can idle and wait for spot.
        # Otherwise, use on-demand to reduce risk while still being flexible.
        threshold = 2.0 * gap
        if slack > threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
