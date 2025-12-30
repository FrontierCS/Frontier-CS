import json
from argparse import Namespace
from typing import Any, Callable, Optional, Sequence, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _ct(name: str) -> ClusterType:
    v = getattr(ClusterType, name, None)
    if v is None and name == "NONE":
        v = getattr(ClusterType, "None", None)
    if v is None:
        raise AttributeError(f"ClusterType missing member {name}")
    return v


CT_SPOT = _ct("SPOT")
CT_ON_DEMAND = _ct("ON_DEMAND")
CT_NONE = _ct("NONE")


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        self._reset_internal_state()
        return self

    def _reset_internal_state(self) -> None:
        self._initialized = False
        self._num_regions = 0
        self._gap = 0.0

        self._done_work = 0.0
        self._last_done_len = 0

        self._last_elapsed: Optional[float] = None
        self._locked_on_demand = False

        self._spot_query_mode = 0
        self._spot_query: Any = None

        self._ema_avail: Optional[list[float]] = None
        self._ema_alpha = 0.05

        self._overhead_pause_allowed: Optional[bool] = None
        self._paused_overhead_probe = False
        self._probe_overhead_value: float = 0.0

        self._none_streak = 0
        self._no_spot_any_streak = 0

    def _ensure_initialized(self, current_has_spot: bool) -> None:
        if self._initialized:
            return
        self._gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if self._gap <= 0:
            self._gap = 60.0
        self._num_regions = int(self.env.get_num_regions())
        self._ema_avail = [0.5] * self._num_regions
        self._detect_spot_query(current_has_spot)
        self._initialized = True

    def _task_duration_seconds(self) -> float:
        td = getattr(self, "task_duration", None)
        if isinstance(td, (int, float)):
            return float(td)
        tds = getattr(self, "task_durations", None)
        if isinstance(tds, Sequence) and tds:
            return float(tds[0])
        tdh = getattr(self, "task_duration_hours", None)
        if isinstance(tdh, Sequence) and tdh:
            return float(tdh[0]) * 3600.0
        raise AttributeError("Cannot find task duration attribute")

    def _deadline_seconds(self) -> float:
        dl = getattr(self, "deadline", None)
        if isinstance(dl, (int, float)):
            return float(dl)
        dlh = getattr(self, "deadline_hours", None)
        if isinstance(dlh, (int, float)):
            return float(dlh) * 3600.0
        raise AttributeError("Cannot find deadline attribute")

    def _restart_overhead_seconds(self) -> float:
        oh = getattr(self, "restart_overhead", None)
        if isinstance(oh, (int, float)):
            return float(oh)
        ohs = getattr(self, "restart_overhead_hours", None)
        if isinstance(ohs, Sequence) and ohs:
            return float(ohs[0]) * 3600.0
        raise AttributeError("Cannot find restart overhead attribute")

    def _detect_spot_query(self, current_has_spot: bool) -> None:
        env = self.env
        n = int(self.env.get_num_regions())
        cur = int(self.env.get_current_region())
        cur_has_spot = bool(current_has_spot)

        def _accept_call_idx(fn: Callable[[int], Any]) -> bool:
            try:
                v = fn(cur)
                if isinstance(v, (bool, int)):
                    return bool(v) == cur_has_spot
            except TypeError:
                return False
            except Exception:
                return False
            return False

        def _accept_call_list(fn: Callable[[], Any]) -> bool:
            try:
                v = fn()
                if hasattr(v, "__len__") and len(v) == n:
                    return bool(v[cur]) == cur_has_spot
            except Exception:
                return False
            return False

        candidates = [
            "is_spot_available",
            "get_spot_available",
            "spot_available",
            "has_spot",
            "get_has_spot",
            "get_spot_availability",
            "get_spot",
            "spot",
            "spot_status",
            "get_spot_status",
        ]

        for name in candidates:
            fn = getattr(env, name, None)
            if callable(fn) and _accept_call_idx(fn):
                self._spot_query_mode = 1
                self._spot_query = fn
                return

        for name in candidates:
            fn = getattr(env, name, None)
            if callable(fn) and _accept_call_list(fn):
                self._spot_query_mode = 2
                self._spot_query = fn
                return

        try:
            for name in dir(env):
                if "spot" not in name.lower():
                    continue
                attr = getattr(env, name, None)
                if isinstance(attr, (list, tuple)) and len(attr) == n and bool(attr[cur]) == cur_has_spot:
                    self._spot_query_mode = 3
                    self._spot_query = name
                    return
                if hasattr(attr, "shape") and getattr(attr, "shape", None) is not None:
                    try:
                        if int(attr.shape[0]) == n and bool(attr[cur]) == cur_has_spot:
                            self._spot_query_mode = 3
                            self._spot_query = name
                            return
                    except Exception:
                        pass
                if isinstance(attr, dict) and (cur in attr) and bool(attr[cur]) == cur_has_spot:
                    self._spot_query_mode = 4
                    self._spot_query = name
                    return
        except Exception:
            pass

        self._spot_query_mode = 0
        self._spot_query = None

    def _spot_available(self, region_idx: int, current_region: int, current_has_spot: bool) -> bool:
        if region_idx == current_region:
            return bool(current_has_spot)
        mode = self._spot_query_mode
        if mode == 0:
            return False
        env = self.env
        try:
            if mode == 1:
                return bool(self._spot_query(region_idx))
            if mode == 2:
                v = self._spot_query()
                return bool(v[region_idx])
            if mode == 3:
                v = getattr(env, self._spot_query)
                return bool(v[region_idx])
            if mode == 4:
                v = getattr(env, self._spot_query)
                return bool(v.get(region_idx, False))
        except Exception:
            return False
        return False

    def _update_done_work(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return
        l = len(tdt)
        if l < self._last_done_len:
            self._done_work = float(sum(tdt))
            self._last_done_len = l
            return
        if l == self._last_done_len:
            return
        self._done_work += float(sum(tdt[self._last_done_len : l]))
        self._last_done_len = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if self._last_elapsed is not None and elapsed + 1e-9 < self._last_elapsed:
            self._reset_internal_state()
        self._last_elapsed = elapsed

        self._ensure_initialized(has_spot)

        if self._paused_overhead_probe and self._overhead_pause_allowed is None:
            if float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0) < self._probe_overhead_value - 1e-9:
                self._overhead_pause_allowed = True
            else:
                self._overhead_pause_allowed = False
            self._paused_overhead_probe = False

        self._update_done_work()
        task_duration = self._task_duration_seconds()
        remaining_work = max(0.0, task_duration - self._done_work)
        if remaining_work <= 1e-9:
            self._none_streak = 0
            return CT_NONE

        deadline = self._deadline_seconds()
        restart_overhead = self._restart_overhead_seconds()
        remaining_time = max(0.0, deadline - elapsed)
        gap = self._gap

        safety = max(2.0 * gap, restart_overhead, 1.0)
        cur_region = int(self.env.get_current_region())

        remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if last_cluster_type == CT_ON_DEMAND:
            od_overhead_time = max(0.0, remaining_overhead)
        else:
            od_overhead_time = restart_overhead

        need_time_if_od = remaining_work + od_overhead_time
        if self._locked_on_demand or (remaining_time <= need_time_if_od + safety):
            self._locked_on_demand = True
            self._none_streak = 0
            return CT_ON_DEMAND

        def safe_to_pause_one_step() -> bool:
            rt = remaining_time - gap
            if rt <= 0:
                return False
            return rt > (remaining_work + restart_overhead + safety)

        if remaining_overhead > 1e-9 and self._overhead_pause_allowed is not False:
            if safe_to_pause_one_step():
                if self._overhead_pause_allowed is None:
                    self._paused_overhead_probe = True
                    self._probe_overhead_value = remaining_overhead
                self._none_streak += 1
                return CT_NONE
            self._overhead_pause_allowed = False

        if self._ema_avail is not None:
            if self._spot_query_mode != 0:
                any_spot = False
                best_idx = -1
                best_score = -1.0
                for i in range(self._num_regions):
                    avail_i = self._spot_available(i, cur_region, has_spot)
                    if avail_i:
                        any_spot = True
                    ema = self._ema_avail[i]
                    x = 1.0 if avail_i else 0.0
                    ema = (1.0 - self._ema_alpha) * ema + self._ema_alpha * x
                    self._ema_avail[i] = ema
                    if avail_i:
                        score = ema
                        if i == cur_region:
                            score += 1.0
                        if score > best_score:
                            best_score = score
                            best_idx = i
                if any_spot:
                    self._no_spot_any_streak = 0
                    if best_idx == cur_region:
                        self._none_streak = 0
                        return CT_SPOT
                    if remaining_overhead <= 1e-9:
                        try:
                            self.env.switch_region(int(best_idx))
                            self._none_streak = 0
                            return CT_SPOT
                        except Exception:
                            pass
                    if safe_to_pause_one_step():
                        self._none_streak += 1
                        return CT_NONE
                    self._none_streak = 0
                    return CT_ON_DEMAND
                else:
                    self._no_spot_any_streak += 1
            else:
                ema = self._ema_avail[cur_region]
                x = 1.0 if has_spot else 0.0
                self._ema_avail[cur_region] = (1.0 - self._ema_alpha) * ema + self._ema_alpha * x
                if has_spot:
                    self._no_spot_any_streak = 0
                    self._none_streak = 0
                    return CT_SPOT
                self._no_spot_any_streak += 1

        if safe_to_pause_one_step():
            self._none_streak += 1
            return CT_NONE

        self._none_streak = 0
        return CT_ON_DEMAND