from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_scheduling_solution_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path for configuration.
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    # Internal helpers

    def _ensure_episode_state(self):
        """Reset per-episode state when a new episode starts."""
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        last_elapsed = getattr(self, "_last_elapsed", None)

        # New episode detected if elapsed time goes backwards or no history yet.
        if last_elapsed is None or elapsed < last_elapsed:
            # Per-episode flags
            self._locked_to_od = False
        self._last_elapsed = elapsed

    def _estimate_progress(self) -> float:
        """Conservative estimate of completed work (in seconds)."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        for seg in segments:
            if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                # Assume [start, end]; if not, this underestimates (safe).
                try:
                    s = float(seg[0])
                    e = float(seg[1])
                except (TypeError, ValueError):
                    continue
                val = e - s
                if val > 0:
                    total += val
            else:
                # Fallback: treat as a duration
                try:
                    v = float(seg)
                except (TypeError, ValueError):
                    continue
                if v > 0:
                    total += v

        # Clamp to task_duration to avoid numerical drift
        td = getattr(self, "task_duration", None)
        if td is not None:
            if total > td:
                total = td
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure per-episode initialization
        self._ensure_episode_state()

        # Initialize lock flag if missing (for very first call ever)
        if not hasattr(self, "_locked_to_od"):
            self._locked_to_od = False

        # Basic environment attributes (all in seconds)
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        task_duration = self.task_duration

        # Estimate progress and remaining work (conservative)
        progress = self._estimate_progress()
        remaining = max(0.0, task_duration - progress)

        # If task seems done, no need to run more
        if remaining <= 0.0:
            return ClusterType.NONE

        # Compute current slack
        slack = deadline - elapsed

        # Safety margin: at least one restart_overhead plus one time step
        safety_margin = restart_overhead + gap

        # Possibly lock to on-demand if we are getting tight on slack
        if not self._locked_to_od:
            # Time required to finish if we switch to on-demand now:
            # one restart overhead plus remaining work (using conservative remaining).
            t_needed_od = restart_overhead + remaining

            # If slack is close to or below (needed + margin), lock to OD.
            # This ensures we don't "gamble" with spot too close to the deadline.
            if slack <= t_needed_od + safety_margin:
                self._locked_to_od = True

        # Once locked, always choose on-demand until done
        if self._locked_to_od:
            return ClusterType.ON_DEMAND

        # Not locked yet: opportunistically use spot when available,
        # otherwise fall back to on-demand to keep making progress.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.ON_DEMAND