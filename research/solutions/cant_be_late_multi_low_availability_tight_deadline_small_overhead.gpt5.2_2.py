import json
from argparse import Namespace
from typing import Any, Callable, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_scan_v1"

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

        self._spot_query_kind: str = "unset"  # unset/attr_bool/attr_seq/method0/method1/none
        self._spot_query_name: Optional[str] = None
        self._spot_query_fn0: Optional[Callable[[], Any]] = None
        self._spot_query_fn1: Optional[Callable[[int], Any]] = None
        self._can_scan_regions: Optional[bool] = None

        self._done_work_sum: float = 0.0
        self._done_work_len: int = 0

        self._rr_next_region: int = 0
        return self

    def _get_task_duration_seconds(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)) and td:
            return float(td[0])
        return float(td)

    def _get_deadline_seconds(self) -> float:
        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)) and dl:
            return float(dl[0])
        return float(dl)

    def _get_restart_overhead_seconds(self) -> float:
        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)) and ro:
            return float(ro[0])
        return float(ro)

    def _get_remaining_restart_overhead_seconds(self) -> float:
        rro = getattr(self, "remaining_restart_overhead", 0.0)
        if isinstance(rro, (list, tuple)) and rro:
            return float(rro[0])
        return float(rro)

    def _update_done_work_sum(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._done_work_sum = 0.0
            self._done_work_len = 0
            return
        n = len(tdt)
        if n == self._done_work_len:
            return
        if n < self._done_work_len:
            self._done_work_sum = float(sum(tdt))
            self._done_work_len = n
            return
        self._done_work_sum += float(sum(tdt[self._done_work_len : n]))
        self._done_work_len = n

    def _detect_spot_query(self) -> None:
        env = self.env
        num_regions = 1
        try:
            num_regions = int(env.get_num_regions())
        except Exception:
            num_regions = 1

        attr_candidates = (
            "has_spot",
            "spot_available",
            "spot_avail",
            "spot_availability",
            "current_has_spot",
            "_has_spot",
            "_spot_available",
        )
        for name in attr_candidates:
            try:
                if not hasattr(env, name):
                    continue
                val = getattr(env, name)
                if isinstance(val, (bool, int)) and not isinstance(val, (list, tuple, dict)):
                    self._spot_query_kind = "attr_bool"
                    self._spot_query_name = name
                    return
                if isinstance(val, (list, tuple)) and len(val) >= num_regions:
                    self._spot_query_kind = "attr_seq"
                    self._spot_query_name = name
                    return
                if isinstance(val, dict):
                    self._spot_query_kind = "attr_dict"
                    self._spot_query_name = name
                    return
            except Exception:
                continue

        method_candidates = (
            "get_has_spot",
            "is_spot_available",
            "spot_available",
            "get_spot_available",
            "get_spot_availability",
            "has_spot",
        )
        for name in method_candidates:
            try:
                fn = getattr(env, name, None)
                if not callable(fn):
                    continue
                try:
                    v0 = fn()
                    if isinstance(v0, (bool, int)):
                        self._spot_query_kind = "method0"
                        self._spot_query_name = name
                        self._spot_query_fn0 = fn
                        return
                except TypeError:
                    pass
                except Exception:
                    pass
                try:
                    cur = int(env.get_current_region())
                    v1 = fn(cur)
                    if isinstance(v1, (bool, int)):
                        self._spot_query_kind = "method1"
                        self._spot_query_name = name
                        self._spot_query_fn1 = fn
                        return
                except TypeError:
                    pass
                except Exception:
                    pass
            except Exception:
                continue

        self._spot_query_kind = "none"
        self._spot_query_name = None

    def _spot_available_current_region(
        self, entry_region: int, entry_has_spot: bool
    ) -> Optional[bool]:
        env = self.env
        kind = self._spot_query_kind

        if kind == "unset":
            self._detect_spot_query()
            kind = self._spot_query_kind

        try:
            if kind == "attr_bool":
                return bool(getattr(env, self._spot_query_name))  # type: ignore[arg-type]
            if kind == "attr_seq":
                seq = getattr(env, self._spot_query_name)  # type: ignore[arg-type]
                return bool(seq[int(env.get_current_region())])
            if kind == "attr_dict":
                dct = getattr(env, self._spot_query_name)  # type: ignore[arg-type]
                cur = int(env.get_current_region())
                if cur in dct:
                    return bool(dct[cur])
                if str(cur) in dct:
                    return bool(dct[str(cur)])
                return None
            if kind == "method0" and self._spot_query_fn0 is not None:
                return bool(self._spot_query_fn0())
            if kind == "method1" and self._spot_query_fn1 is not None:
                return bool(self._spot_query_fn1(int(env.get_current_region())))
        except Exception:
            return None

        if int(env.get_current_region()) == int(entry_region):
            return bool(entry_has_spot)
        return None

    def _init_can_scan_regions(self, entry_region: int, entry_has_spot: bool) -> None:
        if self._can_scan_regions is not None:
            return
        env = self.env
        num_regions = int(env.get_num_regions())
        if num_regions <= 1:
            self._can_scan_regions = False
            return
        if self._spot_query_kind == "unset":
            self._detect_spot_query()
        if self._spot_query_kind == "none":
            self._can_scan_regions = False
            return

        cur = int(env.get_current_region())
        try:
            v_cur = self._spot_available_current_region(entry_region, entry_has_spot)
            env.switch_region((cur + 1) % num_regions)
            v_other = self._spot_available_current_region(entry_region, entry_has_spot)
            env.switch_region(cur)
            self._can_scan_regions = (v_cur is not None) and (v_other is not None)
        except Exception:
            try:
                env.switch_region(cur)
            except Exception:
                pass
            self._can_scan_regions = False

    def _find_region_with_spot(
        self, entry_region: int, entry_has_spot: bool
    ) -> Tuple[int, bool]:
        env = self.env
        cur = int(env.get_current_region())
        v = self._spot_available_current_region(entry_region, entry_has_spot)
        if v is True:
            return cur, True
        if self._can_scan_regions is not True:
            return cur, False

        num_regions = int(env.get_num_regions())
        for off in range(1, num_regions):
            ridx = (cur + off) % num_regions
            env.switch_region(ridx)
            vv = self._spot_available_current_region(entry_region, entry_has_spot)
            if vv is True:
                return ridx, True

        env.switch_region(cur)
        return cur, False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        entry_region = int(env.get_current_region())

        self._update_done_work_sum()
        task_duration = self._get_task_duration_seconds()
        deadline = self._get_deadline_seconds()
        restart_overhead = self._get_restart_overhead_seconds()
        remaining_restart_overhead = self._get_remaining_restart_overhead_seconds()

        remaining_work = task_duration - self._done_work_sum
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - float(getattr(env, "elapsed_seconds", 0.0))
        if time_left <= 1e-9:
            return ClusterType.ON_DEMAND

        gap = float(getattr(env, "gap_seconds", 1.0))
        slack = time_left - remaining_work

        commit_margin = 2.0 * gap + 5.0 * restart_overhead + max(0.0, remaining_restart_overhead)
        pause_threshold = 6.0 * gap

        self._init_can_scan_regions(entry_region, has_spot)

        if remaining_restart_overhead > 1e-9:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT:
                cur_spot = self._spot_available_current_region(entry_region, has_spot)
                if cur_spot is True:
                    return ClusterType.SPOT

        tight = slack <= commit_margin

        if tight and last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        if self._can_scan_regions is True:
            spot_region, spot_any = self._find_region_with_spot(entry_region, has_spot)
            if spot_any:
                if tight and last_cluster_type == ClusterType.ON_DEMAND:
                    return ClusterType.ON_DEMAND
                if last_cluster_type == ClusterType.ON_DEMAND and slack <= pause_threshold:
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            if tight or slack <= pause_threshold:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        if has_spot:
            return ClusterType.SPOT

        if tight or slack <= pause_threshold:
            return ClusterType.ON_DEMAND

        num_regions = int(env.get_num_regions())
        if num_regions > 1:
            try:
                self._rr_next_region = (entry_region + 1) % num_regions
                env.switch_region(self._rr_next_region)
            except Exception:
                pass
        return ClusterType.NONE
