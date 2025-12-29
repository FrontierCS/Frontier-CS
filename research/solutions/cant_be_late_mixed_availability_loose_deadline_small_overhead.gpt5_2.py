import math
from typing import Any, List, Tuple, Union
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


def _sum_completed_work(segments: Any) -> float:
    total = 0.0
    if segments is None:
        return 0.0
    try:
        for seg in segments:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
            elif isinstance(seg, (list, tuple)):
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    total += max(0.0, float(seg[1]) - float(seg[0]))
                elif len(seg) == 1 and isinstance(seg[0], (int, float)):
                    total += float(seg[0])
            elif isinstance(seg, dict):
                if 'duration' in seg and isinstance(seg['duration'], (int, float)):
                    total += float(seg['duration'])
                elif 'start' in seg and 'end' in seg and isinstance(seg['start'], (int, float)) and isinstance(seg['end'], (int, float)):
                    total += max(0.0, float(seg['end']) - float(seg['start']))
    except Exception:
        # Fallback: best-effort sum if unexpected structure
        try:
            total = float(sum(float(x) for x in segments if isinstance(x, (int, float))))
        except Exception:
            total = 0.0
    return max(0.0, total)


class Solution(Strategy):
    NAME = "cant_be_late_robust_v1"

    def __init__(self, args=None):
        super().__init__(args)
        # State to prevent risky flip-flops near the deadline
        self._committed_to_od = False
        # Parameters for safety buffer
        self._static_reserve_sec = 0.0
        self._gap_factor = 1.0
        self._overhead_factor = 1.2
        self._min_buffer_sec = 0.0  # keep lean; we compute from gap/overhead dynamically

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _emergency_buffer_seconds(self, gap: float, overhead: float) -> float:
        # Ensure we have enough to absorb an immediate preemption (overhead) plus
        # one decision step delay (gap). Add a small multiplier for safety.
        calc = self._gap_factor * gap + self._overhead_factor * overhead + self._static_reserve_sec
        # Ensure buffer is at least a modest fraction of a step to avoid razor-thin slack
        calc = max(calc, self._min_buffer_sec)
        return calc

    def _remaining_work(self) -> float:
        done = _sum_completed_work(self.task_done_time)
        return max(0.0, float(self.task_duration) - done)

    def _should_commit_to_od(self, slack: float, buffer_sec: float) -> bool:
        # Commit when we can no longer safely tolerate immediate preemption or step delay.
        return slack <= buffer_sec

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task already complete, no need to run
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time parameters
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        time_left = max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))
        overhead = float(self.restart_overhead)

        # Slack is how much non-progress time we can still afford
        slack = time_left - remaining_work

        # If already late or impossible to finish, best effort: on-demand
        if slack < 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Compute the safety buffer needed to keep feasibility if a preemption hits immediately
        buffer_sec = self._emergency_buffer_seconds(gap, overhead)

        # Decide if we must commit to on-demand to guarantee finish
        if not self._committed_to_od and self._should_commit_to_od(slack, buffer_sec):
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Opportunistic use of spot:
        # - If spot available and we have sufficient slack buffer, use spot
        # - Else if no spot, pause if we have enough slack to afford one step, otherwise use OD
        if has_spot:
            if slack >= buffer_sec:
                return ClusterType.SPOT
            else:
                # If buffer marginal, avoid risk and commit to OD
                self._committed_to_od = True
                return ClusterType.ON_DEMAND
        else:
            # If we can afford to wait one step without breaching the buffer, do so
            if slack >= buffer_sec + gap:
                return ClusterType.NONE
            # Otherwise, switch to OD now to maintain feasibility
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)