import json
import inspect
from argparse import Namespace
from typing import Callable, Optional, List, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None", None)
if _CT_NONE is None:
    _CT_NONE = ClusterType.NONE  # type: ignore[attr-defined]


class Solution(MultiRegionStrategy):
    NAME = "deadline_aware_wait_for_spot"

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

        self._done_work = 0.0
        self._td_len = 0

        self._region_seen: List[int] = []
        self._region_spot: List[int] = []

        self._rr_next = 0
        self._committed_od = False

        self._spot_query_multi: Optional[Callable[[int], bool]] = None
        self._spot_query_inited = False

        self._eps = 1e-9
        return self

    def _ensure_region_stats(self) -> None:
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        if len(self._region_seen) != n:
            self._region_seen = [0] * n
            self._region_spot = [0] * n
            self._rr_next = 0

    def _update_done_work(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n > self._td_len:
            self._done_work += sum(td[self._td_len:n])
            self._td_len = n
        return self._done_work

    def _init_spot_query(self) -> None:
        if self._spot_query_inited:
            return
        self._spot_query_inited = True

        env = self.env
        candidates = [
            "get_has_spot",
            "get_spot_availability",
            "get_spot_available",
            "is_spot_available",
            "spot_available",
            "has_spot_available",
            "has_spot",  # sometimes a method
            "get_region_has_spot",
        ]
        for name in candidates:
            m = getattr(env, name, None)
            if not callable(m):
                continue
            try:
                sig = inspect.signature(m)
                if len(sig.parameters) >= 1:
                    def _wrap(method: Callable[..., Any]) -> Callable[[int], bool]:
                        def f(idx: int) -> bool:
                            return bool(method(idx))
                        return f
                    try:
                        _ = m(0)
                        self._spot_query_multi = _wrap(m)
                        return
                    except Exception:
                        continue
            except Exception:
                continue

        for attr_name in ["spot_availabilities", "spot_available_regions", "spot_availability"]:
            a = getattr(env, attr_name, None)
            if a is None:
                continue
            if isinstance(a, (list, tuple)):
                def _wrap_list(arr: Any) -> Callable[[int], bool]:
                    def f(idx: int) -> bool:
                        try:
                            return bool(arr[idx])
                        except Exception:
                            return False
                    return f
                self._spot_query_multi = _wrap_list(a)
                return

    def _pick_region_with_spot_now(self) -> Optional[int]:
        if self._spot_query_multi is None:
            return None
        n = len(self._region_seen)
        best_idx = None
        best_score = -1.0
        for i in range(n):
            if self._spot_query_multi(i):
                seen = self._region_seen[i]
                spot = self._region_spot[i]
                score = (spot + 1.0) / (seen + 2.0)
                if score > best_score:
                    best_score = score
                    best_idx = i
        return best_idx

    def _switch_round_robin(self, cur: int) -> None:
        n = len(self._region_seen)
        if n <= 1:
            return
        nxt = (cur + 1) % n
        self.env.switch_region(nxt)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_stats()
        if not self._spot_query_inited:
            self._init_spot_query()

        done = self._update_done_work()
        remaining_work = self.task_duration - done
        if remaining_work <= self._eps:
            return _CT_NONE

        t = float(self.env.elapsed_seconds)
        time_left = float(self.deadline - t)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        cur_region = int(self.env.get_current_region())
        if 0 <= cur_region < len(self._region_seen):
            self._region_seen[cur_region] += 1
            if has_spot:
                self._region_spot[cur_region] += 1

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Safety-first: if slack against a continuous OD finish is very small, commit.
        slack_vs_od = time_left - (remaining_work + float(self.restart_overhead))
        if slack_vs_od <= float(self.restart_overhead) + gap:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        if not has_spot:
            # If we can observe other regions' spot status, move to one that has spot now.
            target = self._pick_region_with_spot_now()
            if target is not None and target != cur_region:
                self.env.switch_region(target)
                has_spot = True
                cur_region = target

        if has_spot:
            return ClusterType.SPOT

        # No spot available: wait if still safe to delay by one step and then start OD.
        # (Assume starting OD from idle/non-OD will require full restart_overhead.)
        if gap > 0.0 and (time_left - gap) >= (remaining_work + float(self.restart_overhead) + self._eps):
            self._switch_round_robin(cur_region)
            return _CT_NONE

        # Not safe to wait any longer; commit to OD until completion.
        self._committed_od = True
        return ClusterType.ON_DEMAND
