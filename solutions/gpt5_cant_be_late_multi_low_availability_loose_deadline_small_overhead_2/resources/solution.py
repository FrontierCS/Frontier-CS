import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        self._commit_to_on_demand = False
        return self

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time)
        return max(self.task_duration - done, 0.0)

    def _overhead_if_choose(self, choice: ClusterType, last_cluster_type: ClusterType) -> float:
        # If we keep the same cluster type, we only need to pay the remaining overhead (if any).
        # If we switch, we pay full restart_overhead.
        if choice == last_cluster_type:
            # Continuing on the same cluster consumes remaining overhead.
            return max(self.remaining_restart_overhead, 0.0)
        else:
            return self.restart_overhead

    def _finish_time_if_choose_now(self, choice: ClusterType, last_cluster_type: ClusterType, has_spot: bool) -> Optional[float]:
        # Returns the time the job would finish if we pick `choice` now and stick with it hereafter.
        # For SPOT, this assumes no future preemptions (optimistic); we only use OD for guarantees.
        # For OD, this is exact since OD is not interrupted.
        if choice == ClusterType.NONE:
            return None
        if choice == ClusterType.SPOT and not has_spot:
            return None
        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        rem = self._remaining_work()
        if rem <= 0:
            return t  # already finished
        overhead_now = self._overhead_if_choose(choice, last_cluster_type)
        # Work in this step:
        step_work = max(gap - overhead_now, 0.0)
        step_work = min(step_work, rem)
        rem_after_step = rem - step_work
        t_after_step = t + gap
        # If choosing OD, no interruptions in future:
        if choice == ClusterType.ON_DEMAND:
            return t_after_step + rem_after_step
        # If choosing SPOT and assuming no preemptions, finishing time optimistic:
        return t_after_step + rem_after_step

    def _safe_to_use_spot_one_step(self, last_cluster_type: ClusterType, has_spot: bool) -> bool:
        if not has_spot:
            return False
        # Ensure that even if SPOT disappears next step, switching to OD then still meets deadline.
        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        rem = self._remaining_work()
        if rem <= 0:
            return True
        # Effective work if we pick SPOT now for one step:
        overhead_now = self._overhead_if_choose(ClusterType.SPOT, last_cluster_type)
        work_now = max(gap - overhead_now, 0.0)
        work_now = min(work_now, rem)
        rem_after = rem - work_now
        t_after = t + gap
        # Worst-case: next step we start OD (pay full overhead then) and finish the remaining work.
        # Overhead is restart_overhead at that switch (regardless of remaining).
        finish_time_worst = t_after + self.restart_overhead + rem_after
        return finish_time_worst <= self.deadline + 1e-6

    def _safe_to_wait_none_one_step(self) -> bool:
        # Safe to pause this step if, even after waiting one gap and then switching to OD (with overhead), we can finish.
        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        rem = self._remaining_work()
        if rem <= 0:
            return True
        finish_time_wait_then_od = t + gap + self.restart_overhead + rem
        return finish_time_wait_then_od <= self.deadline + 1e-6

    def _must_choose_od_now(self, last_cluster_type: ClusterType) -> bool:
        # If starting OD at next step would violate deadline, we must start OD now.
        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        rem = self._remaining_work()
        if rem <= 0:
            return False
        # If we delay OD by one step (do NONE or SPOT), then start OD next step:
        finish_next_step_od = t + gap + self.restart_overhead + rem
        return finish_next_step_od > self.deadline + 1e-6

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to OD, stick with it.
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # If task already completed, no need to run further.
        if self._remaining_work() <= 0:
            return ClusterType.NONE

        # Decide action based on safety to meet deadline.
        # Prefer Spot when safe; otherwise use OD. If Spot unavailable and safe to wait, pause.
        if has_spot:
            if self._safe_to_use_spot_one_step(last_cluster_type, has_spot):
                # Use Spot; continue exploiting cheap capacity.
                return ClusterType.SPOT
            else:
                # Not safe to use Spot; commit to OD to guarantee deadline.
                self._commit_to_on_demand = True
                return ClusterType.ON_DEMAND
        else:
            # Spot not available. If we must choose OD now to guarantee deadline, do so; else wait.
            if self._must_choose_od_now(last_cluster_type) or not self._safe_to_wait_none_one_step():
                self._commit_to_on_demand = True
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
