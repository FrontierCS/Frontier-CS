from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "spot_deadline_safe_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Reset internal state for a new evaluation run.
        self._policy_initialized = False
        self._done_idx = 0
        self._done_total = 0.0
        self._commit_to_od = False
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _maybe_init_policy(self):
        if getattr(self, "_policy_initialized", False):
            return
        self._policy_initialized = True

        # Initialize progress cache
        self._done_idx = 0
        self._done_total = 0.0

        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        deadline = getattr(self, "deadline", 0.0) or 0.0
        duration = getattr(self, "task_duration", 0.0) or 0.0

        slack_total = max(deadline - duration, 0.0)

        # Extra buffer on top of restart_overhead to absorb discretization, etc.
        extra_buffer = 0.0
        if slack_total > 0.0:
            # Use min(10% of slack, 2 steps) as extra buffer.
            extra_buffer = min(slack_total * 0.1, 2.0 * gap)

        H = overhead + extra_buffer

        # Ensure H is at least overhead, but not more than total slack.
        if H < overhead:
            H = overhead
        if slack_total > 0.0 and H > slack_total:
            H = slack_total

        self._safety_overhead = H
        self._commit_to_od = False

    def _update_progress_cache(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if lst is None:
            return 0.0

        idx = getattr(self, "_done_idx", 0)
        total = getattr(self, "_done_total", 0.0)
        n = len(lst)

        while idx < n:
            seg = lst[idx]
            dur = 0.0
            if isinstance(seg, (int, float)):
                dur = float(seg)
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                try:
                    dur = float(seg[1]) - float(seg[0])
                except Exception:
                    dur = 0.0
            else:
                d_attr = getattr(seg, "duration", None)
                if d_attr is not None:
                    try:
                        dur = float(d_attr)
                    except Exception:
                        dur = 0.0
            total += dur
            idx += 1

        self._done_idx = idx
        self._done_total = total
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init_policy()

        work_done = self._update_progress_cache()
        remaining = max(self.task_duration - work_done, 0.0)

        # If task is already finished, do nothing.
        if remaining <= 0.0:
            return ClusterType.NONE

        # If we've already decided to stick with on-demand, always use it.
        if getattr(self, "_commit_to_od", False):
            return ClusterType.ON_DEMAND

        t = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        g = getattr(self.env, "gap_seconds", 0.0) or 0.0
        D = getattr(self, "deadline", 0.0) or 0.0
        H = getattr(self, "_safety_overhead", 0.0) or 0.0

        # If there's effectively no slack (or we're already behind), fall back to on-demand.
        if D <= self.task_duration + H + g:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Guard: if even immediate on-demand can't finish, still choose on-demand (best effort).
        if t + remaining + H > D:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Determine whether we can afford to spend the next step not on on-demand.
        # Worst case: we spend this step on SPOT or NONE (no useful progress),
        # then from t + g we immediately switch to on-demand, paying up to H
        # additional overhead, and need `remaining` compute time.
        worst_finish_if_wait = t + g + remaining + H

        if worst_finish_if_wait > D:
            # Can't safely waste this step; must use on-demand.
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # We have enough slack to keep gambling on spot capacity.
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable but we still have slack; wait to avoid on-demand cost.
        return ClusterType.NONE