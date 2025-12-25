from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic"

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _ensure_policy_initialized(self):
        if getattr(self, "_policy_initialized", False):
            return
        env = self.env
        try:
            gap = float(getattr(env, "gap_seconds", 60.0))
        except Exception:
            gap = 60.0
        try:
            deadline = float(self.deadline)
            task_duration = float(self.task_duration)
            base_slack = max(deadline - task_duration, 0.0)
        except Exception:
            base_slack = 3600.0  # default 1 hour if unavailable
        try:
            ovh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            ovh = 0.0

        min_unit = max(1.0, gap, ovh)

        # Critical slack: when we must always use on-demand
        critical = 4.0 * min_unit
        if base_slack > 0.0:
            critical = min(critical, 0.5 * base_slack)
        if critical <= 0.0:
            critical = min_unit

        # Wait slack: above this, if no spot we can pause (NONE)
        wait_slack = max(2.0 * critical, 0.5 * base_slack)
        if base_slack > 0.0:
            wait_slack = min(wait_slack, 0.9 * base_slack)

        self._critical_slack = critical
        self._wait_slack = max(wait_slack, self._critical_slack)
        self._base_slack = base_slack
        self._policy_initialized = True

    def _estimate_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        try:
            n = len(tdt)
            if n == 0:
                return 0.0
        except TypeError:
            return 0.0

        candidates = []

        # Case 1: scalar entries (could be durations or cumulative)
        try:
            scalar_vals = []
            for x in tdt:
                if isinstance(x, (int, float)):
                    scalar_vals.append(float(x))
            if scalar_vals:
                sumv = sum(v for v in scalar_vals if v > 0.0)
                lastv = float(scalar_vals[-1])
                if sumv > 0.0:
                    candidates.append(sumv)
                if lastv > 0.0:
                    candidates.append(lastv)
        except Exception:
            pass

        # Case 2: iterable entries, e.g., (start, end) or (start, duration)
        try:
            first = tdt[0]
            if isinstance(first, (list, tuple)) and len(first) >= 2:
                total = 0.0
                last_end = 0.0
                for seg in tdt:
                    try:
                        a = float(seg[0])
                        b = float(seg[1])
                        if b >= a and a >= 0.0:
                            dur = b - a
                        elif b >= 0.0:
                            dur = b
                        else:
                            dur = 0.0
                        if dur > 0.0:
                            total += dur
                        if b > last_end:
                            last_end = b
                    except Exception:
                        continue
                if total > 0.0:
                    candidates.append(total)
                if last_end > 0.0:
                    candidates.append(last_end)
        except Exception:
            pass

        if not candidates:
            return 0.0

        # Conservative: choose minimal non-negative candidate
        work = min(c for c in candidates if c >= 0.0)

        # Clamp by elapsed time and total task duration to avoid over-estimation
        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = None
        T = getattr(self, "task_duration", None)
        try:
            T = float(T) if T is not None else None
        except Exception:
            T = None

        upper = None
        if elapsed is not None and T is not None:
            upper = min(T, elapsed)
        elif elapsed is not None:
            upper = elapsed
        elif T is not None:
            upper = T

        if upper is not None and work > upper:
            work = upper
        if work < 0.0:
            work = 0.0
        return work

    def _step(self, last_cluster_type: "ClusterType", has_spot: bool) -> "ClusterType":
        self._ensure_policy_initialized()

        env = self.env
        try:
            t = float(env.elapsed_seconds)
        except Exception:
            t = 0.0

        work_done = self._estimate_work_done()

        try:
            T = float(self.task_duration)
        except Exception:
            T = 0.0

        remaining_work = max(T - work_done, 0.0)

        try:
            deadline = float(self.deadline)
        except Exception:
            # If deadline missing, act conservatively: always run on-demand
            return ClusterType.ON_DEMAND

        remaining_time = deadline - t

        # If already out of time or very tight, force on-demand
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work  # how much idle time remains

        # Hard safety: if we are at or past zero slack, must use on-demand
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        critical = self._critical_slack
        wait_slack = self._wait_slack

        # When slack very small, always on-demand regardless of spot availability
        if slack <= critical:
            return ClusterType.ON_DEMAND

        # Prefer spot whenever available while we still have reasonable slack
        if has_spot:
            return ClusterType.SPOT

        # No spot available here
        # If slack is still large, we can afford to wait without incurring cost
        if slack > wait_slack:
            return ClusterType.NONE

        # Slack is moderate and no spot; fall back to on-demand to avoid getting late
        return ClusterType.ON_DEMAND