import json
from argparse import Namespace
from typing import Optional, List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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

        self._inited = False
        self._committed_on_demand = False

        self._task_done_len = 0
        self._work_done_total = 0.0

        self._num_regions = 1
        self._region_seen = []
        self._region_spot_yes = []

        self._spot_query_mode = "unknown"  # unknown | direct_list | direct_idx | switch | none

        return self

    def _init_once(self) -> None:
        if self._inited:
            return
        self._inited = True

        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1

        self._region_seen = [0] * self._num_regions
        self._region_spot_yes = [0] * self._num_regions

        self._task_done_len = 0
        self._work_done_total = 0.0
        self._committed_on_demand = False
        self._spot_query_mode = "unknown"

    def _update_work_done(self) -> float:
        td = self.task_done_time
        ln = len(td)
        if ln < self._task_done_len:
            self._task_done_len = 0
            self._work_done_total = 0.0
        if ln > self._task_done_len:
            delta = td[self._task_done_len:ln]
            self._work_done_total += float(sum(delta)) if delta else 0.0
            self._task_done_len = ln
        return self._work_done_total

    def _get_has_spot_current(self, fallback: Optional[bool] = None) -> Optional[bool]:
        env = self.env
        for name in ("has_spot", "spot_available", "is_spot_available", "get_has_spot", "get_spot_available"):
            attr = getattr(env, name, None)
            if attr is None:
                continue
            try:
                if callable(attr):
                    return bool(attr())
                if isinstance(attr, (bool, int)):
                    return bool(attr)
            except Exception:
                pass
        return bool(fallback) if fallback is not None else None

    def _get_all_spot_availability(self) -> Optional[List[Optional[bool]]]:
        env = self.env
        candidates = (
            "get_spot_availability_all",
            "get_spot_availabilities",
            "get_spot_availability",
            "spot_availability_all",
            "spot_availabilities",
        )
        for name in candidates:
            attr = getattr(env, name, None)
            if attr is None:
                continue
            try:
                if callable(attr):
                    res = attr()
                else:
                    res = attr
                if res is None:
                    continue
                if isinstance(res, (list, tuple)):
                    out = [None] * self._num_regions
                    m = min(len(res), self._num_regions)
                    for i in range(m):
                        v = res[i]
                        out[i] = None if v is None else bool(v)
                    return out
            except Exception:
                pass
        return None

    def _get_has_spot_region_direct(self, idx: int) -> Optional[bool]:
        env = self.env
        for name in ("has_spot", "get_has_spot", "spot_available", "is_spot_available", "get_spot_available"):
            attr = getattr(env, name, None)
            if attr is None or not callable(attr):
                continue
            try:
                return bool(attr(idx))
            except TypeError:
                continue
            except Exception:
                continue
        return None

    def _scan_regions_for_spot(self, fallback_current: Optional[bool]) -> Tuple[Optional[int], Optional[bool]]:
        if self._num_regions <= 1:
            hs = self._get_has_spot_current(fallback_current)
            return (self.env.get_current_region(), hs) if hs else (None, hs)

        env = self.env
        orig = None
        try:
            orig = int(env.get_current_region())
        except Exception:
            orig = 0

        # Try list-based query.
        if self._spot_query_mode in ("unknown", "direct_list"):
            all_av = self._get_all_spot_availability()
            if all_av is not None and len(all_av) >= 1:
                self._spot_query_mode = "direct_list"
                best_idx = None
                best_score = -1e18
                for i, v in enumerate(all_av[: self._num_regions]):
                    if v is None:
                        continue
                    self._region_seen[i] += 1
                    if v:
                        self._region_spot_yes[i] += 1
                        score = (self._region_spot_yes[i] + 1.0) / (self._region_seen[i] + 2.0)
                        if i == orig:
                            score += 1e-6
                        if score > best_score:
                            best_score = score
                            best_idx = i
                if best_idx is not None:
                    return best_idx, True
                return None, False

        # Try direct region-index query.
        if self._spot_query_mode in ("unknown", "direct_idx"):
            any_direct = False
            best_idx = None
            best_score = -1e18
            for i in range(self._num_regions):
                v = self._get_has_spot_region_direct(i)
                if v is None:
                    continue
                any_direct = True
                self._region_seen[i] += 1
                if v:
                    self._region_spot_yes[i] += 1
                    score = (self._region_spot_yes[i] + 1.0) / (self._region_seen[i] + 2.0)
                    if i == orig:
                        score += 1e-6
                    if score > best_score:
                        best_score = score
                        best_idx = i
            if any_direct:
                self._spot_query_mode = "direct_idx"
                if best_idx is not None:
                    return best_idx, True
                return None, False

        # Switch-based probing (may be the only way).
        if self._spot_query_mode in ("unknown", "switch"):
            best_idx = None
            best_score = -1e18
            any_known = False
            for i in range(self._num_regions):
                try:
                    env.switch_region(i)
                except Exception:
                    pass

                v = self._get_has_spot_current(fallback_current if i == orig else None)
                if v is None:
                    continue
                any_known = True
                self._region_seen[i] += 1
                if v:
                    self._region_spot_yes[i] += 1
                    score = (self._region_spot_yes[i] + 1.0) / (self._region_seen[i] + 2.0)
                    if i == orig:
                        score += 1e-6
                    if score > best_score:
                        best_score = score
                        best_idx = i
            if any_known:
                self._spot_query_mode = "switch"
                if best_idx is not None:
                    return best_idx, True
                return None, False

        self._spot_query_mode = "none"
        hs = self._get_has_spot_current(fallback_current)
        return (orig, hs) if hs else (None, hs)

    def _best_region_by_history(self) -> int:
        if self._num_regions <= 1:
            return 0
        best_idx = 0
        best_score = -1.0
        for i in range(self._num_regions):
            seen = self._region_seen[i]
            yes = self._region_spot_yes[i]
            score = (yes + 1.0) / (seen + 2.0)
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        work_done = self._update_work_done()
        work_remaining = self.task_duration - work_done
        if work_remaining <= 0:
            return _CT_NONE

        now = float(self.env.elapsed_seconds)
        time_remaining = self.deadline - now
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)

        restart_overhead = float(self.restart_overhead)
        safety = max(2.0 * gap, 4.0 * restart_overhead)

        required_if_start_od_now = work_remaining + restart_overhead

        if self._committed_on_demand or (time_remaining <= required_if_start_od_now + safety):
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available in any region (scan only if not committed).
        current_has_spot = self._get_has_spot_current(fallback=has_spot)

        use_spot = False
        chosen_region = None

        if current_has_spot is True:
            # If currently on-demand, switch to spot only if it's still worth it.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if time_remaining > required_if_start_od_now + 2.0 * safety and work_remaining > 2.0 * gap:
                    use_spot = True
                else:
                    use_spot = False
            else:
                use_spot = True
        else:
            # If spot isn't available locally, search other regions for spot.
            best_idx, found = self._scan_regions_for_spot(fallback_current=has_spot)
            if found and best_idx is not None:
                chosen_region = best_idx
                use_spot = True
            else:
                use_spot = False

        if use_spot:
            if chosen_region is not None:
                try:
                    if int(self.env.get_current_region()) != int(chosen_region):
                        self.env.switch_region(int(chosen_region))
                except Exception:
                    pass
            # Validate again if possible; fallback to conservative behavior if unknown.
            post_has_spot = self._get_has_spot_current(fallback=has_spot)
            if post_has_spot is True:
                return ClusterType.SPOT
            # If we cannot confirm, avoid risking an invalid SPOT action.
            # Choose NONE or ON_DEMAND based on feasibility below.

        # No confirmed spot: decide NONE vs ON_DEMAND.
        # If we skip one more step, ensure we can still finish on-demand later with safety.
        safe_to_pause = (time_remaining - gap) > (work_remaining + restart_overhead + safety)
        if safe_to_pause:
            # While waiting, bias toward historically good region.
            if self._num_regions > 1:
                best_wait = self._best_region_by_history()
                try:
                    if int(self.env.get_current_region()) != int(best_wait):
                        self.env.switch_region(int(best_wait))
                except Exception:
                    pass
            return _CT_NONE

        self._committed_on_demand = True
        return ClusterType.ON_DEMAND