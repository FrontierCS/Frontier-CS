from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._safe_delay_margin = None
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional: load configuration from spec_path if needed.
        return self

    def _compute_remaining_work(self) -> float:
        done = 0.0
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return float(self.task_duration)

        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    start, end = seg[0], seg[1]
                    done += float(end) - float(start)
                else:
                    done += float(seg)
            except Exception:
                # Be robust to any unexpected format; ignore malformed entries.
                continue

        remaining = float(self.task_duration) - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _init_safe_margin_if_needed(self):
        if self._safe_delay_margin is not None:
            return

        # Obtain gap and slack; fall back gracefully if attributes missing.
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)

        slack_total = max(0.0, deadline - task_duration)

        # Base margin: a few restart_overheads plus several steps of slack.
        base_margin = restart_overhead * 2.0 + gap * 4.0

        # Ensure at least enough to cover one overhead + one step.
        min_margin = restart_overhead + gap

        # Do not consume all slack; keep at most half of total slack as margin.
        if slack_total > 0.0:
            max_reasonable_margin = slack_total * 0.5
            safe_margin = min(base_margin, max_reasonable_margin)
        else:
            safe_margin = base_margin

        safe_margin = max(min_margin, safe_margin)
        self._safe_delay_margin = safe_margin

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_safe_margin_if_needed()

        # If we've already committed to on-demand, keep using it.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        remaining_work = self._compute_remaining_work()
        if remaining_work <= 0.0:
            # Work is done (or effectively done); no need to run more.
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)

        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already past deadline; best effort: run on-demand.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Decide whether it's still safe to delay progress (use SPOT/NONE)
        # or if we must commit to on-demand to finish in time.
        if time_left <= remaining_work + self._safe_delay_margin:
            # Not enough slack to risk further delays; commit to on-demand.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # We have sufficient slack; use spot if available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT

        # No spot this step, but still enough slack to wait for cheaper capacity.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)