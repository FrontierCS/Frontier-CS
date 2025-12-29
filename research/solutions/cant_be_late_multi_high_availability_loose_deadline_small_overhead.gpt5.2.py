import json
import os
import pickle
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


_TRACE_CACHE: Dict[str, bytearray] = {}


def _to_bit(v: Any) -> int:
    if v is None:
        return 0
    if isinstance(v, (bool, int)):
        return 1 if int(v) != 0 else 0
    if isinstance(v, float):
        return 1 if v > 0.0 else 0
    s = str(v).strip()
    if not s:
        return 0
    sl = s.lower()
    if sl in ("1", "true", "t", "yes", "y", "on"):
        return 1
    if sl in ("0", "false", "f", "no", "n", "off"):
        return 0
    try:
        return 1 if float(s) > 0.0 else 0
    except Exception:
        return 0


def _extract_sequence(obj: Any) -> Optional[Sequence[Any]]:
    if obj is None:
        return None
    if isinstance(obj, (list, tuple)):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "spot", "has_spot", "spot_available", "data", "trace", "values"):
            if k in obj and isinstance(obj[k], (list, tuple)):
                return obj[k]
        return None
    return None


def _trace_from_sequence(seq: Sequence[Any]) -> bytearray:
    out = bytearray()
    append = out.append
    for x in seq:
        if isinstance(x, (list, tuple)) and x:
            append(_to_bit(x[-1]))
        elif isinstance(x, dict):
            val = None
            for k in ("availability", "avail", "spot", "has_spot", "spot_available", "value", "v"):
                if k in x:
                    val = x[k]
                    break
            append(_to_bit(val))
        else:
            append(_to_bit(x))
    return out


def _load_trace_file(path: str) -> bytearray:
    cached = _TRACE_CACHE.get(path)
    if cached is not None:
        return cached

    data: Optional[bytearray] = None
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        raw = b""

    if raw:
        # NPY/NPZ
        if np is not None and (raw[:6] == b"\x93NUMPY" or path.endswith(".npy") or path.endswith(".npz")):
            try:
                if path.endswith(".npz"):
                    with np.load(path, allow_pickle=True) as z:
                        if "arr_0" in z:
                            arr = z["arr_0"]
                        else:
                            first_key = next(iter(z.files))
                            arr = z[first_key]
                else:
                    arr = np.load(path, allow_pickle=True)
                arr = np.asarray(arr).reshape(-1)
                data = bytearray(int(x) & 1 for x in arr.tolist())
            except Exception:
                data = None

        # Pickle
        if data is None and (raw[:2] == b"\x80\x04" or path.endswith((".pkl", ".pickle"))):
            try:
                obj = pickle.loads(raw)
                seq = _extract_sequence(obj)
                if seq is not None:
                    data = _trace_from_sequence(seq)
            except Exception:
                data = None

        # JSON
        if data is None:
            s0 = raw.lstrip()[:1]
            if s0 in (b"[", b"{"):
                try:
                    obj = json.loads(raw.decode("utf-8", errors="ignore"))
                    seq = _extract_sequence(obj)
                    if seq is not None:
                        data = _trace_from_sequence(seq)
                except Exception:
                    data = None

        # Text/CSV fallback
        if data is None:
            try:
                txt = raw.decode("utf-8", errors="ignore")
                lines = txt.splitlines()
                out = bytearray()
                append = out.append
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "," in line:
                        token = line.split(",")[-1].strip()
                    elif "\t" in line:
                        token = line.split("\t")[-1].strip()
                    else:
                        parts = line.split()
                        token = parts[-1] if parts else ""
                    append(_to_bit(token))
                if out:
                    data = out
            except Exception:
                data = None

    if data is None:
        data = bytearray()

    _TRACE_CACHE[path] = data
    return data


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_strategy"

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

        self._trace_files: List[str] = list(config.get("trace_files", [])) if isinstance(config.get("trace_files", []), list) else []
        self._raw_traces: List[bytearray] = []
        for p in self._trace_files:
            try:
                self._raw_traces.append(_load_trace_file(p))
            except Exception:
                self._raw_traces.append(bytearray())

        self._precomputed = False
        self._traces: List[bytearray] = []
        self._streaks: List[array] = []
        self._any_spot: bytearray = bytearray()
        self._cum_any: array = array("I")
        self._avg_avail: List[float] = []
        self._T = 0

        self._td_len = 0
        self._work_done = 0.0

        return self

    def _update_progress(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n == self._td_len:
            return
        if self._td_len == 0 and n <= 16:
            self._work_done = float(sum(td))
        else:
            self._work_done += float(sum(td[self._td_len :]))
        self._td_len = n

    def _ensure_precomputed(self) -> None:
        if self._precomputed:
            return

        try:
            R = int(self.env.get_num_regions())
        except Exception:
            R = len(self._raw_traces)

        if R <= 0:
            self._precomputed = True
            return

        raw = self._raw_traces[:R]
        if not raw or all(len(x) == 0 for x in raw):
            self._precomputed = True
            return

        # Determine required horizon length in steps (extend traces if needed).
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        needed_steps = int(self.deadline // gap) + 8
        lengths = [len(x) for x in raw if len(x) > 0]
        if not lengths:
            self._precomputed = True
            return

        T = max(max(lengths), needed_steps)
        traces: List[bytearray] = []
        avg_avail: List[float] = []
        for r in range(R):
            tr = raw[r] if r < len(raw) else bytearray()
            if len(tr) == 0:
                tr = bytearray([0]) * T
            elif len(tr) < T:
                last = tr[-1]
                tr = tr + bytearray([last]) * (T - len(tr))
            elif len(tr) > T:
                tr = tr[:T]
            traces.append(tr)
            avg_avail.append((sum(tr) / float(T)) if T > 0 else 0.0)

        any_spot = bytearray(T)
        for t in range(T):
            v = 0
            for r in range(R):
                if traces[r][t]:
                    v = 1
                    break
            any_spot[t] = v

        cum_any = array("I", [0]) * (T + 1)
        c = 0
        for t in range(T - 1, -1, -1):
            if any_spot[t]:
                c += 1
            cum_any[t] = c

        streaks: List[array] = []
        for r in range(R):
            st = array("I", [0]) * (T + 1)
            tr = traces[r]
            run = 0
            for t in range(T - 1, -1, -1):
                if tr[t]:
                    run += 1
                else:
                    run = 0
                st[t] = run
            streaks.append(st)

        self._traces = traces
        self._streaks = streaks
        self._any_spot = any_spot
        self._cum_any = cum_any
        self._avg_avail = avg_avail
        self._T = T
        self._precomputed = True

    def _choose_best_spot_region(self, idx: int, last_cluster_type: ClusterType) -> int:
        R = len(self._traces)
        if R <= 1:
            return 0
        cur = int(self.env.get_current_region())
        if idx < 0:
            idx = 0
        if idx >= self._T:
            idx = self._T - 1

        gap = float(self.env.gap_seconds)
        switch_penalty = float(self.restart_overhead)

        best_r = -1
        best_score = -1e30
        best_avg = -1.0

        for r in range(R):
            if not self._traces[r][idx]:
                continue
            streak = float(self._streaks[r][idx])
            score = streak * gap
            if r != cur:
                score -= switch_penalty
            avg = self._avg_avail[r]
            if score > best_score or (score == best_score and avg > best_avg) or (score == best_score and avg == best_avg and r == cur):
                best_score = score
                best_avg = avg
                best_r = r

        if best_r < 0:
            return cur
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_progress()

        task_duration = float(self.task_duration)
        remaining_work = task_duration - self._work_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        overhead_pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        required_wall = remaining_work + overhead_pending

        panic_margin = max(2.0 * gap, 4.0 * float(self.restart_overhead))
        if remaining_time <= required_wall + panic_margin:
            self._ensure_precomputed()
            if self._precomputed and self._traces:
                idx = int(elapsed // gap) if gap > 0 else 0
                if idx < 0:
                    idx = 0
                if idx >= self._T:
                    idx = self._T - 1
                cur = int(self.env.get_current_region())
                if 0 <= cur < len(self._traces) and self._traces[cur][idx]:
                    if float(self._streaks[cur][idx]) * gap >= required_wall:
                        return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        self._ensure_precomputed()

        if self._precomputed and self._traces:
            idx = int(elapsed // gap) if gap > 0 else 0
            if idx < 0:
                idx = 0
            if idx >= self._T:
                idx = self._T - 1

            if self._any_spot[idx]:
                best_r = self._choose_best_spot_region(idx, last_cluster_type)
                cur = int(self.env.get_current_region())
                if best_r != cur:
                    try:
                        self.env.switch_region(best_r)
                    except Exception:
                        pass
                return ClusterType.SPOT

            # No spot anywhere now: decide pause vs on-demand based on remaining required work
            future_spot_steps = int(self._cum_any[idx + 1]) if (idx + 1) <= self._T else 0
            future_spot_capacity = float(future_spot_steps) * gap
            safety_work = float(self.restart_overhead) + 0.5 * gap
            if remaining_work > future_spot_capacity + safety_work:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        # No trace-based multi-region info; use simple online fallback.
        if has_spot:
            return ClusterType.SPOT

        if remaining_time <= required_wall + max(gap, float(self.restart_overhead) * 2.0):
            return ClusterType.ON_DEMAND
        return ClusterType.NONE