import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_ONDEMAND = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None")


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._commit_on_demand = False
        self._no_spot_streak = 0
        self._last_switch_elapsed = -1e30
        self._region_seen = None
        self._region_avail = None
        return self

    def reset(self, *args, **kwargs):
        if hasattr(super(), "reset"):
            super().reset(*args, **kwargs)
        self._commit_on_demand = False
        self._no_spot_streak = 0
        self._last_switch_elapsed = -1e30
        self._region_seen = None
        self._region_avail = None

    def _ensure_region_stats(self):
        if self._region_seen is not None and self._region_avail is not None:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        self._region_seen = [0] * n
        self._region_avail = [0] * n

    def _progress_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        return float(sum(tdt))

    def _buffer_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        return 2.0 * oh + 0.2 * gap

    def _on_demand_overhead_if_start_now(self, last_cluster_type) -> float:
        if last_cluster_type == _CT_ONDEMAND:
            return float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        return float(getattr(self, "restart_overhead", 0.0) or 0.0)

    def _maybe_switch_region_while_waiting(self, slack: float) -> None:
        self._ensure_region_stats()
        n = len(self._region_seen)
        if n <= 1:
            return

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if now - self._last_switch_elapsed < 2.0 * gap:
            return
        if slack <= 4.0 * gap:
            return
        if self._no_spot_streak < 2:
            return

        cur = int(self.env.get_current_region())
        # Round-robin switch, but slightly prefer regions with better observed availability.
        best = cur
        best_score = -1.0
        for i in range(n):
            seen = self._region_seen[i]
            avail = self._region_avail[i]
            score = (avail + 1.0) / (seen + 2.0)  # Beta(1,1) prior
            if score > best_score:
                best_score = score
                best = i

        nxt = best
        if nxt == cur:
            nxt = (cur + 1) % n

        if nxt != cur:
            try:
                self.env.switch_region(nxt)
                self._last_switch_elapsed = now
                self._no_spot_streak = 0
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_stats()

        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < len(self._region_seen):
            self._region_seen[cur_region] += 1
            if has_spot:
                self._region_avail[cur_region] += 1

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        done = self._progress_done()
        rem_work = task_duration - done
        if rem_work <= 0.0:
            self._commit_on_demand = False
            return _CT_NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            self._commit_on_demand = True
            return _CT_ONDEMAND

        slack = time_left - rem_work
        buf = self._buffer_seconds()
        od_oh = self._on_demand_overhead_if_start_now(last_cluster_type)

        if self._commit_on_demand:
            return _CT_ONDEMAND

        if time_left <= rem_work + od_oh + buf:
            self._commit_on_demand = True
            return _CT_ONDEMAND

        if has_spot:
            self._no_spot_streak = 0
            return _CT_SPOT

        self._no_spot_streak += 1

        # Consider switching region while we wait (no cost step) to increase chance of spot next step.
        self._maybe_switch_region_while_waiting(slack)

        # Wait if it's still safe to finish with on-demand even if spot never returns.
        # Conservative: if we wait this whole step, then later we may need restart_overhead again.
        restart_oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if (time_left - gap) > (rem_work + restart_oh + buf):
            return _CT_NONE

        self._commit_on_demand = True
        return _CT_ONDEMAND