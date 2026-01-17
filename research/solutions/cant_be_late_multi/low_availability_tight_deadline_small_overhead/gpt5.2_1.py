import json
import gzip
from argparse import Namespace
from array import array
from typing import List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_maybe_gzip(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "rt", encoding="utf-8", errors="ignore")


def _extract_list_from_json(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "spot", "data", "trace", "values"):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list):
                return v
    return None


def _parse_trace_values(values) -> List[int]:
    out = []
    for x in values:
        if isinstance(x, bool):
            out.append(1 if x else 0)
        elif isinstance(x, (int, float)):
            out.append(1 if float(x) > 0.0 else 0)
        elif isinstance(x, str):
            s = x.strip()
            if not s:
                continue
            try:
                out.append(1 if float(s) > 0.0 else 0)
            except Exception:
                ls = s.lower()
                if ls in ("true", "t", "yes", "y", "spot", "available", "avail", "1"):
                    out.append(1)
                elif ls in ("false", "f", "no", "n", "0", "none", "unavailable", "na"):
                    out.append(0)
        elif isinstance(x, dict):
            for k in ("spot", "availability", "avail", "available"):
                if k in x:
                    try:
                        out.append(1 if float(x[k]) > 0.0 else 0)
                    except Exception:
                        out.append(1 if bool(x[k]) else 0)
                    break
    return out


def _read_trace_file(path: str) -> List[int]:
    try:
        with _open_maybe_gzip(path) as f:
            s = f.read()
    except Exception:
        return []

    s_strip = s.lstrip()
    if not s_strip:
        return []

    if s_strip[0] in "[{":
        try:
            obj = json.loads(s_strip)
            lst = _extract_list_from_json(obj)
            if lst is None:
                return []
            return _parse_trace_values(lst)
        except Exception:
            pass

    out = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0] in ("#", "%"):
            continue
        if "," in line:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if not parts:
                continue
            token = parts[-1]
        else:
            parts = line.split()
            token = parts[-1] if parts else ""
        if not token:
            continue
        try:
            out.append(1 if float(token) > 0.0 else 0)
        except Exception:
            tl = token.lower()
            if tl in ("true", "t", "yes", "y", "1", "spot", "available", "avail"):
                out.append(1)
            elif tl in ("false", "f", "no", "n", "0", "none", "unavailable", "na"):
                out.append(0)
            else:
                continue
    return out


def _resample_availability(data: List[int], n_steps: int) -> List[int]:
    if n_steps <= 0:
        return []
    if not data:
        return [0] * n_steps
    m = len(data)
    if m == n_steps:
        return data[:]
    if m < n_steps:
        if n_steps % m == 0:
            k = n_steps // m
            out = [0] * n_steps
            j = 0
            for v in data:
                vv = 1 if v else 0
                for _ in range(k):
                    out[j] = vv
                    j += 1
            return out
        out = data[:]
        out.extend([0] * (n_steps - m))
        return out
    if m > n_steps:
        if m % n_steps == 0:
            k = m // n_steps
            out = [0] * n_steps
            for i in range(n_steps):
                start = i * k
                chunk = data[start : start + k]
                out[i] = 1 if any(chunk) else 0
            return out
        return data[:n_steps]
    return data[:n_steps]


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config, dict) else []

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._gap = float(getattr(self.env, "gap_seconds", 3600.0))
        self._deadline_seconds = float(self.deadline)
        self._task_duration_seconds = float(self.task_duration)
        self._restart_overhead_seconds = float(self.restart_overhead)

        self._num_regions = int(self.env.get_num_regions())
        self._n_steps = int(self._deadline_seconds // self._gap + 1)

        self._spot_price_per_hour = 0.9701
        self._ondemand_price_per_hour = 3.06
        diff = self._ondemand_price_per_hour - self._spot_price_per_hour
        if diff <= 1e-12:
            self._switch_break_even_seconds = float("inf")
        else:
            self._switch_break_even_seconds = (self._ondemand_price_per_hour * self._restart_overhead_seconds) / diff

        self._spot_by_region: List[bytearray] = []
        for r in range(self._num_regions):
            data = []
            if r < len(self._trace_files) and self._trace_files[r]:
                data = _read_trace_file(self._trace_files[r])
            data = _resample_availability(data, self._n_steps)
            self._spot_by_region.append(bytearray(data))

        self._streak_by_region: List[array] = []
        for r in range(self._num_regions):
            avail = self._spot_by_region[r]
            streak = array("I", [0]) * (self._n_steps + 1)
            run = 0
            for i in range(self._n_steps - 1, -1, -1):
                if avail[i]:
                    run += 1
                else:
                    run = 0
                streak[i] = run
            self._streak_by_region.append(streak)

        self._done_work = 0.0
        self._done_idx = 0
        self._trace_offset = 0
        self._obs_hist: List[Tuple[int, int, bool]] = []
        self._mismatch_count = 0
        self._offset_search_range = min(2000, max(0, self._n_steps - 1))
        self._offset_update_period = 200
        self._last_offset_update_t = -10**9

        self._switch_hysteresis_steps = 1

        return self

    def _update_done_work(self) -> None:
        td = self.task_done_time
        n = len(td)
        while self._done_idx < n:
            self._done_work += float(td[self._done_idx])
            self._done_idx += 1

    def _trace_idx(self, t: int) -> int:
        idx = t + self._trace_offset
        if idx < 0:
            return -1
        if idx >= self._n_steps:
            return -1
        return idx

    def _availability(self, region: int, t: int, observed_current_region: Optional[Tuple[int, bool]] = None) -> int:
        if observed_current_region is not None:
            cur_region, has_spot = observed_current_region
            if region == cur_region:
                return 1 if has_spot else 0
        idx = self._trace_idx(t)
        if idx < 0:
            return 0
        return 1 if self._spot_by_region[region][idx] else 0

    def _streak(self, region: int, t: int) -> int:
        idx = self._trace_idx(t)
        if idx < 0:
            return 0
        return int(self._streak_by_region[region][idx])

    def _maybe_update_offset(self, t: int, region: int, has_spot: bool) -> None:
        if not self._spot_by_region:
            return

        idx = self._trace_idx(t)
        if idx >= 0:
            pred = bool(self._spot_by_region[region][idx])
            if pred != bool(has_spot):
                self._mismatch_count += 1

        self._obs_hist.append((t, region, bool(has_spot)))
        if len(self._obs_hist) > 30:
            self._obs_hist.pop(0)

        if t - self._last_offset_update_t < self._offset_update_period and self._mismatch_count < 5:
            return

        self._last_offset_update_t = t
        self._mismatch_count = 0

        if not self._obs_hist:
            return

        rmax = self._offset_search_range
        best_off = self._trace_offset
        best_score = -1
        current_score = -1

        def score_offset(off: int) -> int:
            score = 0
            for tt, rr, hs in self._obs_hist:
                idx2 = tt + off
                if idx2 < 0 or idx2 >= self._n_steps:
                    continue
                if bool(self._spot_by_region[rr][idx2]) == hs:
                    score += 1
            return score

        current_score = score_offset(self._trace_offset)
        best_score = current_score

        for off in range(-rmax, rmax + 1):
            if off == self._trace_offset:
                continue
            sc = score_offset(off)
            if sc > best_score:
                best_score = sc
                best_off = off
                if best_score == len(self._obs_hist):
                    break

        if best_score > current_score + 2:
            self._trace_offset = best_off

    def _can_idle_one_step(self, remaining_work: float, time_left: float) -> bool:
        if time_left <= 0:
            return False
        tl = time_left - self._gap
        if tl <= 0:
            return False
        max_work_if_start_later = tl - self._restart_overhead_seconds
        if max_work_if_start_later < 0:
            max_work_if_start_later = 0.0
        return remaining_work <= max_work_if_start_later + 1e-9

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_work()
        remaining_work = self._task_duration_seconds - self._done_work
        if remaining_work <= 0:
            return ClusterType.NONE

        t = int(float(self.env.elapsed_seconds) // self._gap)
        if t < 0:
            t = 0
        if t >= self._n_steps:
            return ClusterType.ON_DEMAND

        cur_region = int(self.env.get_current_region())
        self._maybe_update_offset(t, cur_region, has_spot)

        time_left = self._deadline_seconds - float(self.env.elapsed_seconds)
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        observed = (cur_region, bool(has_spot))

        best_region = -1
        best_streak = -1

        if self._num_regions <= 0 or not self._spot_by_region:
            if has_spot:
                return ClusterType.SPOT
            if self._can_idle_one_step(remaining_work, time_left):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        for r in range(self._num_regions):
            av = self._availability(r, t, observed_current_region=observed)
            if not av:
                continue
            st = self._streak(r, t)
            if st > best_streak:
                best_streak = st
                best_region = r

        if best_region != -1:
            cur_av = self._availability(cur_region, t, observed_current_region=observed)
            if cur_av:
                cur_st = self._streak(cur_region, t)
                if cur_st >= best_streak - self._switch_hysteresis_steps:
                    best_region = cur_region
                    best_streak = cur_st

            slack = time_left - remaining_work
            if slack < 0:
                slack = 0.0

            if last_cluster_type == ClusterType.ON_DEMAND:
                run_seconds = float(best_streak) * self._gap
                if slack < self._restart_overhead_seconds * 1.2:
                    return ClusterType.ON_DEMAND
                if run_seconds < self._switch_break_even_seconds:
                    return ClusterType.ON_DEMAND

            if best_region != cur_region:
                self.env.switch_region(best_region)

            return ClusterType.SPOT

        if self._can_idle_one_step(remaining_work, time_left):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND