from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # No pre-processing needed; configuration is dynamic per environment.
        return self

    def _compute_work_done(self) -> float:
        """Robustly compute total work done from self.task_done_time."""
        task_done = getattr(self, "task_done_time", None)
        if task_done is None:
            return 0.0

        # If it's already a numeric total
        if isinstance(task_done, (int, float)):
            return float(task_done)

        total = 0.0
        # Try to treat as iterable of segments
        try:
            for seg in task_done:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                else:
                    # Try (start, end)
                    try:
                        s = seg[0]
                        e = seg[1]
                        total += float(e) - float(s)
                        continue
                    except Exception:
                        pass
                    # Try attribute 'duration'
                    try:
                        dur = getattr(seg, "duration", None)
                        if dur is not None:
                            total += float(dur)
                    except Exception:
                        # Ignore unrecognized segment formats
                        pass
        except TypeError:
            # Not iterable; fallback: treat as zero
            return 0.0

        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Basic environment values
        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        dt = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", now))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Progress so far
        done = self._compute_work_done()
        remaining = task_duration - done
        if remaining <= 0.0:
            # Task already done; no need to run anything.
            return ClusterType.NONE

        time_left = deadline - now
        if time_left <= 0.0:
            # Already at or past deadline – still try to run OD to finish ASAP.
            return ClusterType.ON_DEMAND

        # Total slack for this task/environment (time_left - remaining at t=0 is deadline - task_duration)
        total_slack = max(0.0, float(deadline - task_duration))
        slack_now = time_left - remaining

        # Safety slack: reserve a fraction of total slack, but not too small.
        # This is the minimum slack we aim to maintain when deciding to idle.
        base_safety_slack = total_slack * 0.2  # 20% of total slack
        min_safety_slack = restart_overhead * 3.0 + dt * 5.0  # cover overhead + a few steps
        if total_slack <= 0.0:
            safety_slack = min_safety_slack
        else:
            safety_slack = max(base_safety_slack, min_safety_slack)
            max_safety_allowed = total_slack * 0.8
            if safety_slack > max_safety_allowed:
                safety_slack = max_safety_allowed

        # If spot is available, always use it (cheaper and makes progress).
        # We rely on on-demand only when spot is unavailable and slack is getting tight.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide between idling (NONE) and using expensive on-demand.
        # Predict slack after one idle step (no progress, only time passes).
        slack_after_idle = slack_now - dt

        # If idling would bring us below the safety slack, we must use on-demand now.
        if slack_after_idle < safety_slack:
            return ClusterType.ON_DEMAND

        # Otherwise, we can afford to wait for cheaper spot capacity.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)