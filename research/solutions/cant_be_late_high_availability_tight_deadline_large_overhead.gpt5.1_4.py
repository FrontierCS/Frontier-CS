from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_deadline_safe"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path for config, but we don't need it.
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode by elapsed time reset.
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        last_elapsed = getattr(self, "_last_elapsed", None)
        if last_elapsed is None or elapsed < last_elapsed:
            # New run detected: reset per-run state.
            self.commit_to_od = False
        self._last_elapsed = elapsed

        # Basic environment parameters.
        gap = getattr(self.env, "gap_seconds", 0.0)
        deadline = getattr(self, "deadline", 0.0)
        time_left = deadline - elapsed

        # Compute remaining work.
        task_duration = getattr(self, "task_duration", 0.0)
        task_done_list = getattr(self, "task_done_time", None)
        work_done = 0.0
        if task_done_list:
            try:
                work_done = float(sum(task_done_list))
            except TypeError:
                work_done = 0.0
                for seg in task_done_list:
                    try:
                        work_done += float(seg)
                    except (TypeError, ValueError):
                        continue
        remaining = max(0.0, task_duration - work_done)

        # If task already finished, avoid unnecessary cost.
        if remaining <= 0.0:
            return ClusterType.NONE

        # Safety overhead buffer (seconds).
        safety_overhead = float(getattr(self, "restart_overhead", 0.0))
        # Additional safety margin to account for discretization / rounding.
        margin = float(gap)

        # If already committed to on-demand for this run, always stay on it.
        if getattr(self, "commit_to_od", False):
            return ClusterType.ON_DEMAND

        # If there is effectively no time left, use on-demand (though it's likely too late).
        if time_left <= 0.0:
            self.commit_to_od = True
            return ClusterType.ON_DEMAND

        # Decide whether we can afford a potentially zero-progress interval this step
        # (i.e., using SPOT or NONE).
        time_left_after_interval = time_left - gap
        # Safe to risk unreliable compute (SPOT or NONE) only if, after one more
        # interval of zero progress, we can still switch to ON_DEMAND and finish
        # accounting for restart overhead and a discretization margin.
        can_risk_unreliable = (
            time_left_after_interval >= remaining + safety_overhead + margin
        )

        if not can_risk_unreliable:
            # Need to ensure completion: commit to ON_DEMAND for the rest of the run.
            self.commit_to_od = True
            return ClusterType.ON_DEMAND

        # We have enough slack to risk unreliable progress this step.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and still enough slack: wait for spot to save cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        if parser is None:
            args = None
        else:
            args, _ = parser.parse_known_args()
        return cls(args)