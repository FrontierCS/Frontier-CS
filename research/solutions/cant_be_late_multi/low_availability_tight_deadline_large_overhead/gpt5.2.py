import json
import math
import os
from argparse import Namespace
from array import array
from collections import deque
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = ClusterType.SPOT
_CT_OD = ClusterType.ON_DEMAND
_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None")


def _to01(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        return 1 if float(x) > 0.5 else 0
    s = str(x).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return 1
    if s in ("0", "false", "f", "no", "n", "off"):
        return 0
    try:
        v = float(s)
        return 1 if v > 0.5 else 0
    except Exception:
        return 0


def _ceil_div(a: float, b: float) -> int:
    if b <= 0:
        return 0
    return int(math.ceil((a - 1e-12) / b))


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
        self._trace_files = list(config.get("trace_files", []))
        self._prepared = False
        self._use_traces = True
        self._trace_offset = 0
        self._obs = deque(maxlen=200)
        self._mismatch_count = 0
        self._checked_obs = 0

        self._done_sum = 0.0
        self._last_done_len = 0

        self._committed_on_demand = False
        self._commit_buffer_steps = 1
        self._idle_reserve_steps = 1

        super().__init__(args)
        return self

    def _update_done_cache(self) -> None:
        tdt = self.task_done_time
        n = len(tdt)
        if n > self._last_done_len:
            for i in range(self._last_done_len, n):
                self._done_sum += float(tdt[i])
            self._last_done_len = n

    def _parse_trace_file(self, path: str) -> List[int]:
        if not path or not os.path.exists(path):
            return []

        try:
            with open(path, "rb") as f:
                raw = f.read()
        except Exception:
            return []

        txt = None
        try:
            txt = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            txt = ""

        if not txt:
            return []

        if txt[0] in "[{":
            try:
                data = json.loads(txt)
                return self._extract_availability_from_json(data)
            except Exception:
                pass

        vals: List[int] = []
        try:
            for line in txt.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p for p in line.replace("\t", ",").replace(" ", ",").split(",") if p != ""]
                if not parts:
                    continue
                tok = parts[-1]
                vals.append(_to01(tok))
        except Exception:
            return vals
        return vals

    def _extract_availability_from_json(self, data: Any) -> List[int]:
        if isinstance(data, list):
            if not data:
                return []
            if isinstance(data[0], dict):
                keys = ("available", "availability", "spot", "has_spot", "value", "avail")
                out = []
                for item in data:
                    v = None
                    for k in keys:
                        if k in item:
                            v = item[k]
                            break
                    if v is None:
                        out.append(0)
                    else:
                        out.append(_to01(v))
                return out
            return [_to01(x) for x in data]

        if isinstance(data, dict):
            for k in ("availability", "available", "spot", "has_spot", "values", "trace", "data"):
                if k in data and isinstance(data[k], list):
                    return self._extract_availability_from_json(data[k])
        return []

    def _ensure_prepared(self) -> None:
        if self._prepared:
            return

        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 3600.0

        num_regions = None
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = None

        if num_regions is None or num_regions <= 0:
            num_regions = max(1, len(getattr(self, "_trace_files", [])) or 1)

        self._num_regions = num_regions
        self._gap = gap

        try:
            needed_steps = max(1, int(math.ceil(float(self.deadline) / gap)) + 5)
        except Exception:
            needed_steps = 1000

        self._trace_len = needed_steps

        avail_by_region: List[bytearray] = []
        runlen_by_region: List[array] = []
        nextspot_by_region: List[array] = []

        trace_files = getattr(self, "_trace_files", [])
        for r in range(num_regions):
            vals: List[int] = []
            if r < len(trace_files):
                vals = self._parse_trace_file(trace_files[r])

            if not vals:
                avail = bytearray(needed_steps)
            else:
                if len(vals) < needed_steps:
                    vals = vals + [0] * (needed_steps - len(vals))
                elif len(vals) > needed_steps:
                    vals = vals[:needed_steps]
                avail = bytearray(vals)

            avail_by_region.append(avail)

            run = array("I", [0]) * (needed_steps + 1)
            nxt = array("I", [needed_steps]) * (needed_steps + 1)

            next_idx = needed_steps
            streak = 0
            for i in range(needed_steps - 1, -1, -1):
                if avail[i]:
                    streak += 1
                    next_idx = i
                    run[i] = streak
                else:
                    streak = 0
                    run[i] = 0
                nxt[i] = next_idx

            runlen_by_region.append(run)
            nextspot_by_region.append(nxt)

        any_spot = bytearray(needed_steps)
        for i in range(needed_steps):
            a = 0
            for r in range(num_regions):
                if avail_by_region[r][i]:
                    a = 1
                    break
            any_spot[i] = a

        any_next = array("I", [needed_steps]) * (needed_steps + 1)
        any_sufcnt = array("I", [0]) * (needed_steps + 1)
        next_idx = needed_steps
        cnt = 0
        for i in range(needed_steps - 1, -1, -1):
            if any_spot[i]:
                next_idx = i
                cnt += 1
            any_next[i] = next_idx
            any_sufcnt[i] = cnt

        self._avail = avail_by_region
        self._runlen = runlen_by_region
        self._nextspot = nextspot_by_region
        self._any_spot = any_spot
        self._any_next = any_next
        self._any_sufcnt = any_sufcnt

        self._min_spot_run_steps_from_ondemand = max(2, _ceil_div(float(self.restart_overhead), gap) + 1)

        self._prepared = True

    def _t_adj(self, t: int) -> int:
        if not self._prepared:
            return t
        idx = t + int(self._trace_offset)
        if idx < 0:
            return 0
        if idx >= self._trace_len:
            return self._trace_len - 1
        return idx

    def _spot_at(self, region: int, t: int) -> int:
        if not self._prepared or not self._use_traces:
            return 0
        idx = self._t_adj(t)
        if region < 0 or region >= self._num_regions:
            return 0
        return 1 if self._avail[region][idx] else 0

    def _spot_runlen(self, region: int, t: int) -> int:
        if not self._prepared or not self._use_traces:
            return 0
        idx = self._t_adj(t)
        if region < 0 or region >= self._num_regions:
            return 0
        return int(self._runlen[region][idx])

    def _any_spot_remaining_count(self, t: int) -> int:
        if not self._prepared or not self._use_traces:
            return 0
        idx = self._t_adj(t)
        return int(self._any_sufcnt[idx])

    def _any_spot_next(self, t: int) -> int:
        if not self._prepared or not self._use_traces:
            return self._trace_len
        idx = self._t_adj(t)
        return int(self._any_next[idx])

    def _recalibrate_offset(self) -> None:
        if not (self._prepared and self._use_traces and self._obs):
            return

        offsets = range(-3, 4)
        best_off = self._trace_offset
        best_mis = None
        obs = list(self._obs)
        max_idx = self._trace_len - 1
        for off in offsets:
            mis = 0
            total = 0
            for (t, r, hs) in obs:
                idx = t + off
                if idx < 0:
                    idx = 0
                elif idx > max_idx:
                    idx = max_idx
                tr = 1 if self._avail[r][idx] else 0
                if tr != (1 if hs else 0):
                    mis += 1
                total += 1
            if total == 0:
                continue
            if best_mis is None or mis < best_mis:
                best_mis = mis
                best_off = off

        if best_mis is not None:
            self._trace_offset = int(best_off)
            rate = best_mis / max(1, len(obs))
            if rate > 0.45 and len(obs) >= 40:
                self._use_traces = False

    def _best_spot_region_now(
        self, t: int, current_region: int, has_spot_current: bool
    ) -> Tuple[Optional[int], int]:
        best_r = None
        best_L = -1

        if has_spot_current:
            Lc = self._spot_runlen(current_region, t) if self._use_traces else 1
            best_r = current_region
            best_L = Lc

        if not (self._prepared and self._use_traces):
            return best_r, best_L

        for r in range(self._num_regions):
            if r == current_region:
                continue
            if not self._spot_at(r, t):
                continue
            L = self._spot_runlen(r, t)
            if L > best_L:
                best_L = L
                best_r = r

        return best_r, best_L

    def _should_commit_on_demand(
        self,
        t: int,
        steps_left: int,
        remaining_work: float,
        last_cluster_type: ClusterType,
        current_region: int,
        has_spot_current: bool,
    ) -> bool:
        gap = self._gap

        if last_cluster_type == _CT_OD:
            overhead_needed = float(self.remaining_restart_overhead)
        else:
            overhead_needed = float(self.restart_overhead)

        steps_needed_od = _ceil_div(remaining_work + overhead_needed, gap)

        if steps_left > steps_needed_od + self._commit_buffer_steps:
            return False

        if self._prepared and self._use_traces:
            best_r, best_L = self._best_spot_region_now(t, current_region, has_spot_current)
            if best_r is not None and best_L > 0:
                if best_r == current_region and last_cluster_type == _CT_SPOT:
                    spot_overhead = float(self.remaining_restart_overhead)
                else:
                    spot_overhead = float(self.restart_overhead)
                max_work = max(0.0, best_L * gap - spot_overhead)
                if max_work + 1e-9 >= remaining_work:
                    return False

        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_prepared()

        gap = self._gap
        elapsed = float(self.env.elapsed_seconds)
        t = int(elapsed // gap)

        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0

        if self._prepared and self._use_traces:
            if 0 <= current_region < self._num_regions:
                self._obs.append((t, current_region, bool(has_spot)))
                if len(self._obs) >= 20 and (t % 20 == 0):
                    self._recalibrate_offset()

        self._update_done_cache()
        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 1e-9:
            return _CT_NONE

        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 1e-9:
            return _CT_NONE

        steps_left = int(max(0, math.floor((remaining_time + 1e-9) / gap)))

        if self._committed_on_demand:
            return _CT_OD

        if self._should_commit_on_demand(t, steps_left, remaining_work, last_cluster_type, current_region, has_spot):
            self._committed_on_demand = True
            return _CT_OD

        if last_cluster_type == _CT_OD and float(self.remaining_restart_overhead) > 1e-9:
            return _CT_OD

        best_r, best_L = self._best_spot_region_now(t, current_region, has_spot)

        if best_r is not None:
            if last_cluster_type == _CT_OD:
                if best_L < self._min_spot_run_steps_from_ondemand:
                    return _CT_OD

            if best_r != current_region:
                try:
                    self.env.switch_region(best_r)
                except Exception:
                    pass
            return _CT_SPOT

        if self._prepared and self._use_traces:
            any_future = self._any_spot_remaining_count(t)
            if any_future <= 0:
                return _CT_OD

            steps_needed_work = _ceil_div(remaining_work, gap)
            any_spot_cnt = any_future
            no_spot_cnt = max(0, steps_left - any_spot_cnt)
            needed_od_steps = max(0, steps_needed_work - any_spot_cnt)

            margin = no_spot_cnt - needed_od_steps
            if margin <= self._idle_reserve_steps:
                return _CT_OD

            after_idle_steps_left = steps_left - 1
            steps_needed_od_after_idle = _ceil_div(remaining_work + float(self.restart_overhead), gap)
            if after_idle_steps_left <= steps_needed_od_after_idle + self._commit_buffer_steps:
                return _CT_OD

            return _CT_NONE

        overhead_after_idle = float(self.restart_overhead)
        steps_needed_od_after_idle = _ceil_div(remaining_work + overhead_after_idle, gap)
        if steps_left - 1 <= steps_needed_od_after_idle + self._commit_buffer_steps:
            return _CT_OD
        return _CT_NONE