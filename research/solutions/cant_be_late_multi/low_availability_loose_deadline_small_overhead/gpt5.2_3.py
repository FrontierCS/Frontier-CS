import json
from argparse import Namespace
from typing import Any, Callable, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_aware_v1"

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

        self._committed_to_ondemand = False
        self._cum_done = 0.0
        self._td_len = 0

        self._num_regions_cache: Optional[int] = None
        self._spot_query_fn: Optional[Callable[[int], Optional[bool]]] = None
        self._spot_query_fn_ready: bool = False

        self._region_score = None
        return self

    @staticmethod
    def _ct_none() -> Any:
        return getattr(ClusterType, "NONE", getattr(ClusterType, "None"))

    def _ct_spot(self) -> Any:
        return ClusterType.SPOT

    def _ct_ondemand(self) -> Any:
        return ClusterType.ON_DEMAND

    def _as_scalar_seconds(self, x: Any) -> float:
        if isinstance(x, (list, tuple)):
            if not x:
                return 0.0
            return float(x[0])
        return float(x)

    def _update_cum_done(self) -> None:
        td = getattr(self, "task_done_time", None)
        if not td:
            self._cum_done = 0.0
            self._td_len = 0
            return
        n = len(td)
        if n <= self._td_len:
            return
        s = 0.0
        for i in range(self._td_len, n):
            s += float(td[i])
        self._cum_done += s
        self._td_len = n

    def _get_num_regions(self) -> int:
        if self._num_regions_cache is None:
            try:
                self._num_regions_cache = int(self.env.get_num_regions())
            except Exception:
                self._num_regions_cache = 1
        return self._num_regions_cache

    def _init_region_scores_if_needed(self) -> None:
        if self._region_score is None:
            r = self._get_num_regions()
            self._region_score = [0.0] * r

    def _discover_spot_query(self) -> None:
        if self._spot_query_fn_ready:
            return

        env = self.env
        candidates = (
            "get_has_spot",
            "get_spot",
            "has_spot",
            "get_spot_availability",
            "is_spot_available",
            "spot_available",
            "get_region_has_spot",
            "get_spot_for_region",
        )

        def make_query(meth: Callable[..., Any], mode: int) -> Callable[[int], Optional[bool]]:
            if mode == 1:
                def q(idx: int) -> Optional[bool]:
                    try:
                        v = meth(idx)
                    except Exception:
                        return None
                    if isinstance(v, bool):
                        return v
                    return None
                return q
            elif mode == 2:
                def q(idx: int) -> Optional[bool]:
                    gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
                    t = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
                    step = int(t // gap) if gap > 0 else int(t)
                    try:
                        v = meth(idx, step)
                    except Exception:
                        return None
                    if isinstance(v, bool):
                        return v
                    return None
                return q
            else:
                def q(idx: int) -> Optional[bool]:
                    t = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
                    try:
                        v = meth(idx, t)
                    except Exception:
                        return None
                    if isinstance(v, bool):
                        return v
                    return None
                return q

        found_fn = None
        for name in candidates:
            meth = getattr(env, name, None)
            if not callable(meth):
                continue
            q1 = make_query(meth, 1)
            try:
                test = q1(0)
                if isinstance(test, bool) or test is None:
                    found_fn = q1
                    break
            except Exception:
                pass
            q2 = make_query(meth, 2)
            try:
                test = q2(0)
                if isinstance(test, bool) or test is None:
                    found_fn = q2
                    break
            except Exception:
                pass
            q3 = make_query(meth, 3)
            try:
                test = q3(0)
                if isinstance(test, bool) or test is None:
                    found_fn = q3
                    break
            except Exception:
                pass

        self._spot_query_fn = found_fn
        self._spot_query_fn_ready = True

    def _get_spot_in_region(self, idx: int) -> Optional[bool]:
        self._discover_spot_query()
        if self._spot_query_fn is None:
            return None
        return self._spot_query_fn(idx)

    def _pick_best_spot_region(self, current_region: int) -> Optional[int]:
        self._init_region_scores_if_needed()
        r = self._get_num_regions()

        best_idx = None
        best_score = -1e18
        any_known = False

        for i in range(r):
            avail = self._get_spot_in_region(i)
            if avail is None:
                continue
            any_known = True
            if avail:
                score = self._region_score[i]
                if i == current_region:
                    score += 1e-6
                if score > best_score:
                    best_score = score
                    best_idx = i

        if not any_known:
            return None
        return best_idx

    def _update_region_scores(self, current_region: int, has_spot: bool) -> None:
        self._init_region_scores_if_needed()
        alpha = 0.02
        decay = 1.0 - alpha

        if self._spot_query_fn is None:
            for i in range(len(self._region_score)):
                self._region_score[i] *= decay
            self._region_score[current_region] = self._region_score[current_region] * decay + (alpha if has_spot else 0.0)
            return

        r = self._get_num_regions()
        for i in range(r):
            avail = self._get_spot_in_region(i)
            if avail is None:
                self._region_score[i] *= decay
            else:
                self._region_score[i] = self._region_score[i] * decay + (alpha if avail else 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_cum_done()

        ct_none = self._ct_none()
        ct_spot = self._ct_spot()
        ct_od = self._ct_ondemand()

        task_duration = self._as_scalar_seconds(getattr(self, "task_duration", 0.0))
        deadline = self._as_scalar_seconds(getattr(self, "deadline", 0.0))
        restart_overhead = self._as_scalar_seconds(getattr(self, "restart_overhead", 0.0))

        remaining_work = task_duration - self._cum_done
        if remaining_work <= 0.0:
            return ct_none

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        time_left = deadline - now

        if time_left <= 0.0:
            return ct_od

        current_region = 0
        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0

        self._update_region_scores(current_region, has_spot)

        if last_cluster_type == ct_od:
            overhead_needed = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            overhead_needed = restart_overhead

        safety = max(gap, restart_overhead + 1e-9)

        if not self._committed_to_ondemand:
            if time_left <= remaining_work + overhead_needed + safety:
                self._committed_to_ondemand = True

        if self._committed_to_ondemand:
            return ct_od

        if has_spot:
            return ct_spot

        if gap > 0.0 and restart_overhead >= gap:
            return ct_none

        best_region = self._pick_best_spot_region(current_region)
        if best_region is not None and best_region != current_region:
            try:
                self.env.switch_region(int(best_region))
            except Exception:
                pass
            return ct_spot
        elif best_region == current_region:
            return ct_spot

        return ct_none