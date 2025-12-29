import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_slack_strategy_v1"

    def __init__(self, args):
        super().__init__(args)
        self._initialized = False
        # Fallback absolute thresholds in seconds (used as caps)
        self._panic_slack = 2 * 60 * 60   # 2 hours
        self._relax_slack = 8 * 60 * 60   # 8 hours

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _maybe_initialize(self):
        if self._initialized:
            return
        self._initialized = True

        # Fetch configuration from environment, with robust fallbacks
        total_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", total_duration))
        total_slack = max(deadline - total_duration, 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0))

        if total_slack > 0.0:
            # Relax threshold: fraction of total slack, respecting overhead and upper bound
            relax = 0.4 * total_slack
            min_relax = 4.0 * overhead
            if relax < min_relax:
                relax = min_relax
            max_relax = 0.9 * total_slack
            if relax > max_relax:
                relax = max_relax

            # Panic threshold: smaller fraction of slack, but at least a few overheads
            panic = 0.15 * total_slack
            min_panic = 3.0 * overhead
            if panic < min_panic:
                panic = min_panic
            if panic >= relax:
                panic = 0.5 * relax

            self._relax_slack = float(relax)
            self._panic_slack = float(panic)
        else:
            # No slack: always be in "panic" mode -> fully on-demand
            self._relax_slack = 0.0
            self._panic_slack = 0.0

        # Ensure panic slack is not too tiny compared to overhead
        if overhead > 0.0 and self._panic_slack < 2.0 * overhead:
            self._panic_slack = 2.0 * overhead

        # Ensure relax >= panic
        if self._relax_slack < self._panic_slack:
            self._relax_slack = self._panic_slack

        # Apply absolute caps when there's enough slack (tuned for typical spec)
        abs_relax = 8 * 60 * 60  # 8 hours
        abs_panic = 2 * 60 * 60  # 2 hours
        if total_slack >= abs_relax:
            if self._relax_slack > abs_relax:
                self._relax_slack = abs_relax
            if self._panic_slack > abs_panic:
                self._panic_slack = abs_panic

        # Final safety guard
        if self._relax_slack < self._panic_slack:
            self._relax_slack = self._panic_slack

    def _compute_work_done(self):
        work_done = 0.0
        segments = getattr(self, "task_done_time", [])
        try:
            for seg in segments:
                try:
                    if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                        work_done += float(seg[1]) - float(seg[0])
                    else:
                        work_done += float(seg)
                except Exception:
                    continue
        except Exception:
            work_done = 0.0
        return max(work_done, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_initialize()

        # Remaining work
        total_duration = float(getattr(self, "task_duration", 0.0))
        work_done = self._compute_work_done()
        remaining_work = max(total_duration - work_done, 0.0)

        if remaining_work <= 0.0:
            # Task is already complete
            return ClusterType.NONE

        # Remaining time until deadline
        env = getattr(self, "env", None)
        if env is not None:
            try:
                elapsed = float(env.elapsed_seconds)
            except Exception:
                elapsed = 0.0
        else:
            elapsed = 0.0

        deadline = float(getattr(self, "deadline", elapsed + remaining_work))
        remaining_time = deadline - elapsed

        if remaining_time <= 0.0:
            # Already at or past deadline; best effort is on-demand
            return ClusterType.ON_DEMAND

        # Slack: how much extra time beyond required work we still have
        slack = remaining_time - remaining_work

        # Panic mode: very small slack -> always use on-demand
        if slack <= self._panic_slack:
            return ClusterType.ON_DEMAND

        # Tight but not critical: never idle; use OD if spot unavailable
        if slack <= self._relax_slack:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Relaxed regime: plenty of slack.
        # Prefer spot; if spot unavailable, it's safe to wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)