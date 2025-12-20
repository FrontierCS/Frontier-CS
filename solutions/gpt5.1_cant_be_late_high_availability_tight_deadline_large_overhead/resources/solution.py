import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal state
        self._policy_initialized = False
        self.committed_to_on_demand = False
        self.initial_slack = None
        self.commit_slack = None
        self.mix_slack = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could read spec_path here; unused in this heuristic
        return self

    # --- Internal helpers ---

    def _init_policy(self):
        # Ensure environment attributes exist before initialization
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        self.initial_slack = max(0.0, deadline - task_duration)

        # Commit threshold: once slack gets this low, permanently switch to OD
        # Balance between safety and cost; scaled by initial slack and restart overhead.
        # Units: seconds.
        self.commit_slack = max(
            0.15 * self.initial_slack,  # ~15% of slack
            2.0 * restart_overhead      # at least 2× restart overhead
        )

        # Mixed mode threshold: between pure-spot and must-not-idle regimes.
        # When slack below this, we use OD whenever spot is unavailable.
        self.mix_slack = max(
            2.5 * self.commit_slack,    # ensure clear separation from commit_slack
            0.5 * self.initial_slack    # at least half the initial slack
        )
        # Cap to keep some buffer
        self.mix_slack = min(self.mix_slack, 0.9 * self.initial_slack)

        # Guard against degenerate cases
        if self.mix_slack < self.commit_slack:
            self.mix_slack = self.commit_slack

        self._policy_initialized = True

    def _compute_progress(self) -> float:
        """Best-effort computation of total work done (seconds) from task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total = 0.0
        for seg in segments:
            if seg is None:
                continue
            try:
                # Simple numeric duration
                if isinstance(seg, (int, float)):
                    v = float(seg)
                    if v > 0:
                        total += v
                    continue

                # Tuple or list (possibly [start, end] or [duration])
                if isinstance(seg, (list, tuple)):
                    if len(seg) == 2:
                        s, e = seg
                        total += max(0.0, float(e) - float(s))
                    elif len(seg) == 1:
                        v = float(seg[0])
                        if v > 0:
                            total += v
                    else:
                        # Fallback: use last element as duration
                        v = float(seg[-1])
                        if v > 0:
                            total += v
                    continue

                # Objects with common attributes
                if hasattr(seg, "duration"):
                    v = float(getattr(seg, "duration"))
                    if v > 0:
                        total += v
                    continue

                if hasattr(seg, "start") and hasattr(seg, "end"):
                    s = getattr(seg, "start")
                    e = getattr(seg, "end")
                    total += max(0.0, float(e) - float(s))
                    continue

                if hasattr(seg, "start_time") and hasattr(seg, "end_time"):
                    s = getattr(seg, "start_time")
                    e = getattr(seg, "end_time")
                    total += max(0.0, float(e) - float(s))
                    continue

                # Final fallback: try to interpret as duration
                v = float(seg)
                if v > 0:
                    total += v
            except Exception:
                # Ignore unparseable segment entries
                continue

        # Never exceed required task duration
        try:
            max_duration = float(self.task_duration)
        except Exception:
            max_duration = total
        return min(total, max_duration)

    # --- Core decision logic ---

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy policy initialization (env attributes available now)
        if not self._policy_initialized:
            self._init_policy()

        # Compute progress and remaining work
        done = self._compute_progress()
        try:
            total_required = float(self.task_duration)
        except Exception:
            total_required = done
        remaining_work = max(0.0, total_required - done)

        # If job is done, avoid extra cost
        if remaining_work <= 0.0:
            self.committed_to_on_demand = True
            return ClusterType.NONE

        # Current timing
        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            # No valid deadline; safest is on-demand
            return ClusterType.ON_DEMAND

        time_left = max(0.0, deadline - elapsed)

        # If somehow past deadline, nothing sensible to do; avoid extra cost
        if time_left <= 0.0:
            return ClusterType.NONE

        # Slack measures how much "extra" time we have if compute were uninterrupted
        slack = time_left - remaining_work

        # Safety check: if it's already impossible mathematically, still try OD
        if slack < -self.restart_overhead:
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide if we must permanently commit to on-demand now
        if not self.committed_to_on_demand:
            # Condition 1: slack below commit threshold
            need_commit_by_slack = slack <= self.commit_slack

            # Condition 2: even with immediate switch (and overhead) we are tight
            try:
                restart_overhead = float(self.restart_overhead)
            except Exception:
                restart_overhead = 0.0
            need_commit_by_time = time_left <= remaining_work + restart_overhead

            if need_commit_by_slack or need_commit_by_time:
                self.committed_to_on_demand = True

        # Once committed, always use on-demand to avoid any further risk
        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet committed to OD: opportunistic use of spot with slack-aware fallback

        # If spot is available, it's always the cheapest safe choice before commitment
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide between idling and on-demand based on slack

        # Early in the run with ample slack: we can afford to idle to save cost
        if slack > self.mix_slack:
            return ClusterType.NONE

        # Mid-phase: slack is moderate; avoid further idle losses by using on-demand
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
