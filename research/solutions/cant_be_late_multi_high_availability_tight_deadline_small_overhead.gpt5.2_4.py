import json
from argparse import Namespace
from typing import Callable, List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._spot_vec_fn: Optional[Callable[[], List[bool]]] = None
        self._spot_single_fn: Optional[Callable[[int], bool]] = None
        self._spot_query_inited = False

        self._work_done = 0.0
        self._task_done_len = 0

        self._committed_on_demand = False

        self._spot_seen: List[int] = []
        self._spot_up: List[int] = []

        self._eps = 1e-9
        return self

    def _init_spot_query(self) -> None:
        if self._spot_query_inited:
            return
        self._spot_query_inited = True

        env = self.env

        vec_names = (
            "get_spot_availabilities",
            "get_all_spot_availabilities",
            "spot_availabilities",
            "get_spot_vector",
            "get_spot_vec",
            "get_spot_all",
        )
        for name in vec_names:
            if hasattr(env, name):
                f = getattr(env, name)

                def _vec_fn(f=f, env=env):
                    v = f()
                    if isinstance(v, dict):
                        n = env.get_num_regions()
                        out = [False] * n
                        for k, val in v.items():
                            try:
                                idx = int(k)
                            except Exception:
                                continue
                            if 0 <= idx < n:
                                out[idx] = bool(val)
                        return out
                    return list(v)

                self._spot_vec_fn = _vec_fn
                self._spot_single_fn = None
                return

        single_names = (
            "get_spot_availability",
            "is_spot_available",
            "has_spot",
            "get_has_spot",
            "spot_available",
            "get_spot",
        )
        for name in single_names:
            if hasattr(env, name):
                f = getattr(env, name)

                def _single_fn(idx: int, f=f) -> bool:
                    try:
                        return bool(f(idx))
                    except TypeError:
                        return bool(f())

                self._spot_single_fn = _single_fn
                self._spot_vec_fn = None
                return

        self._spot_vec_fn = None
        self._spot_single_fn = None

    def _update_work_done(self) -> None:
        td = self.task_done_time
        ln = len(td)
        if ln != self._task_done_len:
            if ln > self._task_done_len:
                self._work_done += sum(td[self._task_done_len:ln])
            else:
                self._work_done = sum(td)
            self._task_done_len = ln

    def _get_spot_vec(self, current_has_spot: bool) -> Optional[List[bool]]:
        self._init_spot_query()
        env = self.env
        n = env.get_num_regions()

        vec = None
        if self._spot_vec_fn is not None:
            try:
                vec = self._spot_vec_fn()
            except Exception:
                vec = None
        elif self._spot_single_fn is not None:
            try:
                vec = [bool(self._spot_single_fn(i)) for i in range(n)]
            except Exception:
                vec = None

        if vec is None:
            return None

        if len(vec) != n:
            try:
                vec = list(vec)[:n] + [False] * max(0, n - len(vec))
            except Exception:
                return None

        cur = env.get_current_region()
        if 0 <= cur < n:
            vec[cur] = bool(current_has_spot)

        return vec

    def _pick_best_spot_region(self, spot_vec: List[bool]) -> int:
        env = self.env
        cur = env.get_current_region()
        n = len(spot_vec)

        if self._spot_seen and len(self._spot_seen) != n:
            self._spot_seen = [0] * n
            self._spot_up = [0] * n
        elif not self._spot_seen:
            self._spot_seen = [0] * n
            self._spot_up = [0] * n

        best = -1
        best_score = -1.0

        for i, avail in enumerate(spot_vec):
            if not avail:
                continue
            seen = self._spot_seen[i]
            up = self._spot_up[i]
            score = (up + 1.0) / (seen + 2.0)
            if i == cur:
                score += 1e-6
            if score > best_score:
                best_score = score
                best = i

        if best < 0:
            return cur
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        gap = float(env.gap_seconds)

        self._update_work_done()
        remaining_work = self.task_duration - self._work_done
        if remaining_work <= self._eps:
            return ClusterType.NONE

        remaining_time = self.deadline - float(env.elapsed_seconds)
        if remaining_time <= self._eps:
            return ClusterType.NONE

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # If we have any pending overhead, avoid triggering a new restart unless necessary.
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        # Hard safety condition: when it's too late to risk any further uncertainty, commit to on-demand.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = pending_overhead
        else:
            overhead_needed = float(self.restart_overhead)

        if remaining_time <= remaining_work + overhead_needed + self._eps:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # If overhead is currently counting down, avoid changes that could reset it.
        if pending_overhead > self._eps:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        # Non-urgent: prefer spot; use multi-region switching if we can safely identify a region with spot.
        spot_vec = self._get_spot_vec(has_spot)
        if spot_vec is not None:
            n = len(spot_vec)
            if not self._spot_seen or len(self._spot_seen) != n:
                self._spot_seen = [0] * n
                self._spot_up = [0] * n
            for i, avail in enumerate(spot_vec):
                self._spot_seen[i] += 1
                if avail:
                    self._spot_up[i] += 1

        cur_region = env.get_current_region()

        if has_spot:
            return ClusterType.SPOT

        # Current region has no spot: switch if we can find another region with spot now.
        if spot_vec is not None and any(spot_vec):
            target = self._pick_best_spot_region(spot_vec)
            if target != cur_region:
                try:
                    env.switch_region(target)
                except Exception:
                    pass
            # Ensure we only return SPOT when we believe it's available in the selected region.
            # If switching failed, we might still be in a no-spot region.
            new_region = env.get_current_region()
            if 0 <= new_region < len(spot_vec) and spot_vec[new_region]:
                return ClusterType.SPOT

        # No spot anywhere (or cannot query): wait if slack is healthy; otherwise use on-demand.
        slack = remaining_time - remaining_work
        wait_threshold = max(20.0 * float(self.restart_overhead), 30.0 * gap, 1800.0)
        if slack > wait_threshold:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
