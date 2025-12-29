from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v1"

    def __init__(self, *init_args, **init_kwargs):
        super().__init__(*init_args, **init_kwargs)
        self._reset_internal_state()

    def _reset_internal_state(self):
        self.committed_to_on_demand = False
        self._cached_task_done_sum = 0.0
        self._cached_task_done_len = 0
        self._last_elapsed_seconds = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional: load configuration from spec_path.
        # For now, we use a fixed strategy independent of spec.
        return self

    def _update_cached_progress(self):
        # Incrementally cache the sum of task_done_time to avoid O(n^2) over many steps
        task_done_time = getattr(self, "task_done_time", [])
        current_len = len(task_done_time)
        if current_len != self._cached_task_done_len:
            # Recompute sum when list length changes
            self._cached_task_done_sum = float(sum(task_done_time)) if task_done_time else 0.0
            self._cached_task_done_len = current_len

    def _detect_new_episode(self):
        # Detect environment reset by elapsed_seconds going backwards or first call
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._last_elapsed_seconds is None or elapsed < self._last_elapsed_seconds:
            self._reset_internal_state()
        self._last_elapsed_seconds = elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode and reset per-episode state if needed
        self._detect_new_episode()

        # Update cached progress
        self._update_cached_progress()

        # Compute remaining work (in seconds)
        task_duration = float(self.task_duration)
        work_done = self._cached_task_done_sum
        remaining_work = max(task_duration - work_done, 0.0)

        # If task is already complete, do nothing to avoid extra cost
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we've already committed to on-demand, stick with it until completion
        if self.committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Retrieve timing parameters
        t = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)
        deadline = float(self.deadline)

        # Safety buffer to account for discretization / alignment (2 steps)
        buffer = 2.0 * gap

        # Decide if it's safe to delay committing to on-demand by one more step,
        # under pessimistic assumption of no useful progress during this step.
        # Condition: even if we wait one gap now and then switch to on-demand,
        # we can still finish before the deadline, considering overhead + buffer.
        can_delay_one_step = (
            t + gap + overhead + remaining_work + buffer
        ) <= deadline

        if can_delay_one_step:
            # Still have enough slack to "gamble" on spot or wait for it
            if has_spot:
                return ClusterType.SPOT
            else:
                # Spot unavailable and we have slack: wait without incurring cost
                return ClusterType.NONE
        else:
            # No longer safe to delay: commit to on-demand from now on
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)