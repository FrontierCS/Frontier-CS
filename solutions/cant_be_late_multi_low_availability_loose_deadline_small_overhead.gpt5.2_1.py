import json
import math
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _is_truthy_token(tok: str) -> Optional[int]:
    t = tok.strip().lower()
    if t in ("1", "true", "t", "yes", "y", "on"):
        return 1
    if t in ("0", "false", "f", "no", "n", "off"):
        return 0
    return None


def _extract_series_from_json(obj: Any) -> Optional[List[int]]:
    if isinstance(obj, list):
        out: List[int] = []
        for v in obj:
            if isinstance(v, (int, float)):
                out.append(1 if float(v) > 0.0 else 0)
            elif isinstance(v, str):
                tv = _is_truthy_token(v)
                if tv is None:
                    try:
                        out.append(1 if float(v) > 0.0 else 0)
                    except Exception:
                        continue
                else:
                    out.append(tv)
            elif isinstance(v, dict):
                for k in ("has_spot", "spot", "availability", "avail", "available", "value", "v"):
                    if k in v:
                        vv = v[k]
                        if isinstance(vv, (int, float)):
                            out.append(1 if float(vv) > 0.0 else 0)
                            break
                        if isinstance(vv, str):
                            tvv = _is_truthy_token(vv)
                            if tvv is None:
                                try:
                                    out.append(1 if float(vv) > 0.0 else 0)
                                except Exception:
                                    pass
                            else:
                                out.append(tvv)
                            break
            else:
                continue
        return out if out else None
    if isinstance(obj, dict):
        for k in ("data", "trace", "traces", "values", "availability", "avail", "spot", "has_spot"):
            if k in obj:
                res = _extract_series_from_json(obj[k])
                if res:
                    return res
        return None
    return None


def _read_trace_file(path: str) -> List[int]:
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return []

    if not raw:
        return []

    b0 = raw.lstrip()[:1]
    if b0 in (b"{", b"["):
        try:
            obj = json.loads(raw.decode("utf-8", errors="ignore"))
            series = _extract_series_from_json(obj)
            if series is not None:
                return series
        except Exception:
            pass

    # Text/CSV fallback
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return []

    out: List[int] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s2 = s.replace(",", " ").replace("\t", " ")
        parts = [p for p in s2.split(" ") if p]
        if not parts:
            continue
        val_tok = parts[-1]
        tv = _is_truthy_token(val_tok)
        if tv is not None:
            out.append(tv)
            continue
        try:
            fv = float(val_tok)
            out.append(1 if fv > 0.0 else 0)
            continue
        except Exception:
            pass

        # Try find any numeric/truthy token from right to left
        for tok in reversed(parts):
            tv = _is_truthy_token(tok)
            if tv is not None:
                out.append(tv)
                break
            try:
                fv = float(tok)
                out.append(1 if fv > 0.0 else 0)
                break
            except Exception:
                continue

    return out


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_safe_multiregion"

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

        self._trace_files: List[str] = list(config.get("trace_files", []) or [])
        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            self._raw_traces.append(_read_trace_file(p))

        self._precomp_ready = False
        self._precomp_gap = None
        self._precomp_T = 0
        self._avail: List[bytearray] = []
        self._runlen: List[array] = []
        self._next1: List[array] = []

        self._committed = False
        self._done_sum = 0.0
        self._done_len = 0
        self._last_elapsed = -1.0

        return self

    def _reset_episode_state(self) -> None:
        self._committed = False
        self._done_sum = 0.0
        self._done_len = 0

    def _ensure_precomputed(self) -> None:
        if self.env is None:
            return
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return

        if self._precomp_ready and self._precomp_gap == gap:
            return

        deadline = float(self.deadline) if not isinstance(self.deadline, list) else float(self.deadline[0])
        T_steps = int(math.ceil(deadline / gap)) + 2
        self._precomp_gap = gap
        self._precomp_T = T_steps

        nregions = int(self.env.get_num_regions())
        if nregions <= 0:
            self._precomp_ready = True
            self._avail = []
            self._runlen = []
            self._next1 = []
            return

        raw_traces = self._raw_traces or []
        if not raw_traces:
            self._precomp_ready = True
            self._avail = []
            self._runlen = []
            self._next1 = []
            return

        use_regions = min(nregions, len(raw_traces))
        avail_list: List[bytearray] = []
        runlen_list: List[array] = []
        next1_list: List[array] = []

        INF = T_steps + 10
        for r in range(use_regions):
            raw = raw_traces[r]
            ba = bytearray(T_steps)
            m = min(len(raw), T_steps)
            if m > 0:
                # raw expected 0/1 ints
                for i in range(m):
                    ba[i] = 1 if raw[i] else 0
            # pad rest with 0 by default
            rl = array("I", [0]) * (T_steps + 1)
            nx = array("I", [INF]) * (T_steps + 1)

            # backward compute
            rl[T_steps] = 0
            nx[T_steps] = INF
            for i in range(T_steps - 1, -1, -1):
                if ba[i]:
                    rl[i] = rl[i + 1] + 1
                    nx[i] = i
                else:
                    rl[i] = 0
                    nx[i] = nx[i + 1]

            avail_list.append(ba)
            runlen_list.append(rl)
            next1_list.append(nx)

        self._avail = avail_list
        self._runlen = runlen_list
        self._next1 = next1_list
        self._precomp_ready = True

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n < self._done_len:
            self._done_sum = float(sum(td))
            self._done_len = n
            return
        if n == self._done_len:
            return
        # Incremental add
        self._done_sum += float(sum(td[self._done_len : n]))
        self._done_len = n

    def _get_task_duration_seconds(self) -> float:
        td = self.task_duration
        if isinstance(td, list):
            return float(td[0]) if td else 0.0
        return float(td)

    def _get_restart_overhead_seconds(self) -> float:
        ro = self.restart_overhead
        if isinstance(ro, list):
            return float(ro[0]) if ro else 0.0
        return float(ro)

    def _choose_target_region(self, idx: int) -> Optional[int]:
        if not self._precomp_ready or not self._avail or not self._next1 or not self._runlen:
            return None
        T = self._precomp_T
        if idx >= T - 1:
            return None
        q = idx + 1
        use_regions = len(self._next1)
        INF = T + 10

        best_r = 0
        best_t = INF
        best_len = 0

        for r in range(use_regions):
            t1 = int(self._next1[r][q])
            if t1 >= INF:
                continue
            if t1 < best_t:
                best_t = t1
                best_r = r
                best_len = int(self._runlen[r][t1]) if t1 < len(self._runlen[r]) else 0
            elif t1 == best_t:
                ln = int(self._runlen[r][t1]) if t1 < len(self._runlen[r]) else 0
                if ln > best_len:
                    best_r = r
                    best_len = ln

        if best_t >= INF:
            return None
        return best_r

    def _earliest_next_spot_dt(self, idx: int) -> Optional[float]:
        if not self._precomp_ready or not self._next1:
            return None
        T = self._precomp_T
        if idx >= T - 1:
            return None
        q = idx + 1
        INF = T + 10
        best_t = INF
        for r in range(len(self._next1)):
            t1 = int(self._next1[r][q])
            if t1 < best_t:
                best_t = t1
        if best_t >= INF:
            return float("inf")
        gap = float(self.env.gap_seconds)
        return float(best_t - idx) * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.env is None:
            return ClusterType.ON_DEMAND

        elapsed = float(self.env.elapsed_seconds)
        if self._last_elapsed >= 0.0 and elapsed < self._last_elapsed - 1e-6:
            self._reset_episode_state()
        if elapsed <= 1e-9 and self._last_elapsed > 1e-6:
            self._reset_episode_state()
        self._last_elapsed = elapsed

        self._ensure_precomputed()
        self._update_done_sum()

        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline) if not isinstance(self.deadline, list) else float(self.deadline[0])
        task_duration = self._get_task_duration_seconds()
        restart_overhead = self._get_restart_overhead_seconds()

        remaining_work = task_duration - float(self._done_sum)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 1e-9:
            return ClusterType.NONE

        slack = time_left - remaining_work
        buffer_seconds = restart_overhead + gap

        idx = int(elapsed / gap + 1e-9)

        if self._committed:
            return ClusterType.ON_DEMAND

        # If too close to deadline, commit to on-demand
        if slack <= buffer_seconds:
            self._committed = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot in current region: decide whether we can wait until next likely spot
        dt_next_spot = self._earliest_next_spot_dt(idx)
        if dt_next_spot is None:
            return ClusterType.NONE

        if math.isinf(dt_next_spot):
            # No spot expected: commit once it becomes necessary (use dt=+inf forces commit now if slack finite)
            self._committed = True
            return ClusterType.ON_DEMAND

        if slack <= dt_next_spot + buffer_seconds:
            self._committed = True
            return ClusterType.ON_DEMAND

        # Wait and reposition to a region that will likely have spot soon.
        target = self._choose_target_region(idx)
        if target is not None:
            try:
                if int(self.env.get_current_region()) != int(target):
                    self.env.switch_region(int(target))
            except Exception:
                pass

        return ClusterType.NONE
