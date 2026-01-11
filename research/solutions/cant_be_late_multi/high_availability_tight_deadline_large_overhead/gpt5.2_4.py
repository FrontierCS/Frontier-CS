import json
import math
import os
import pickle
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _ct_none():
    return getattr(ClusterType, "NONE", getattr(ClusterType, "None"))


_CT_NONE = _ct_none()


def _as_scalar(x: Any, default: float = 0.0) -> float:
    if x is None:
        return float(default)
    if isinstance(x, (list, tuple)):
        if not x:
            return float(default)
        return float(x[0])
    try:
        return float(x)
    except Exception:
        return float(default)


def _safe_json_load(path: str) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_sequence_from_obj(obj: Any) -> Optional[Sequence]:
    if obj is None:
        return None
    if isinstance(obj, (list, tuple)):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "spot", "has_spot", "trace", "values", "data"):
            v = obj.get(k)
            if isinstance(v, (list, tuple)):
                return v
        for v in obj.values():
            if isinstance(v, (list, tuple)):
                return v
    return None


def _to_bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return bool(v > 0.5)
    if isinstance(v, str):
        s = v.strip().lower()
        if not s:
            return None
        if s in ("1", "true", "t", "yes", "y", "on"):
            return True
        if s in ("0", "false", "f", "no", "n", "off"):
            return False
        try:
            return float(s) > 0.5
        except Exception:
            return None
    return None


def _load_trace_bool_list(path: str, max_len: int) -> List[int]:
    # Returns list of 0/1 ints, truncated to max_len if >0; may be shorter.
    if not path:
        return []
    try:
        with open(path, "rb") as f:
            head = f.read(2)
        if head[:1] == b"\x80":
            with open(path, "rb") as f:
                obj = pickle.load(f)
            seq = _extract_sequence_from_obj(obj)
            if seq is not None:
                out = []
                for i, v in enumerate(seq):
                    if max_len > 0 and i >= max_len:
                        break
                    bv = _to_bool(v)
                    out.append(1 if bv else 0)
                return out
    except Exception:
        pass

    if path.endswith(".json"):
        obj = _safe_json_load(path)
        seq = _extract_sequence_from_obj(obj)
        if seq is not None:
            out = []
            for i, v in enumerate(seq):
                if max_len > 0 and i >= max_len:
                    break
                bv = _to_bool(v)
                out.append(1 if bv else 0)
            return out

    # Attempt numpy .npy without hard dependency
    if path.endswith(".npy"):
        try:
            import numpy as np  # type: ignore

            arr = np.load(path, allow_pickle=True)
            arr = arr.reshape(-1)
            out = []
            n = int(arr.shape[0])
            if max_len > 0:
                n = min(n, max_len)
            for i in range(n):
                bv = _to_bool(arr[i].item() if hasattr(arr[i], "item") else arr[i])
                out.append(1 if bv else 0)
            return out
        except Exception:
            pass

    # Text/CSV fallback
    out: List[int] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if max_len > 0 and len(out) >= max_len:
                    break
                s = line.strip()
                if not s:
                    continue
                if s[0] in ("#", ";"):
                    continue
                # Try split and find first token parseable as bool/number
                parts = s.replace("\t", " ").replace(",", " ").split()
                bv = None
                for p in parts:
                    bv = _to_bool(p)
                    if bv is not None:
                        break
                if bv is None:
                    continue
                out.append(1 if bv else 0)
    except Exception:
        return []
    return out


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        self._deadline = _as_scalar(getattr(self, "deadline", None), 0.0)
        self._task_duration = _as_scalar(getattr(self, "task_duration", None), 0.0)
        self._restart_overhead = _as_scalar(getattr(self, "restart_overhead", None), 0.0)

        self._done_work = 0.0
        self._done_len = 0

        self._lock_on_demand = False

        self._use_traces = True
        self._trace_offset = 0
        self._mismatch = 0

        self._num_regions = int(getattr(self.env, "get_num_regions")()) if hasattr(self.env, "get_num_regions") else 1
        trace_files = config.get("trace_files", []) or []
        if not isinstance(trace_files, list):
            trace_files = list(trace_files)

        required_steps = int(math.ceil(self._deadline / self._gap)) + 8
        if required_steps <= 0:
            required_steps = 8
        self._N = required_steps

        self._spot: List[bytearray] = []
        self._runlen: List[array] = []
        self._next_spot: List[array] = []
        self._any_spot = bytearray(self._N)
        self._best_region = array("h", [-1] * self._N)
        self._best_runlen = array("I", [0] * self._N)
        self._future_any_spot = array("I", [0] * (self._N + 1))

        try:
            if len(trace_files) < self._num_regions:
                trace_files = trace_files + [""] * (self._num_regions - len(trace_files))
            elif len(trace_files) > self._num_regions:
                trace_files = trace_files[: self._num_regions]

            # Load spot availability
            for r in range(self._num_regions):
                path = trace_files[r]
                seq = _load_trace_bool_list(path, self._N)
                ba = bytearray(self._N)
                L = len(seq)
                if L > 0:
                    ba[:L] = bytearray(seq[:L])
                # Pad unknown tail conservatively with 0 (no spot)
                self._spot.append(ba)

            # Compute run lengths
            for r in range(self._num_regions):
                rl = array("I", [0] * self._N)
                s = self._spot[r]
                nxt = 0
                for t in range(self._N - 1, -1, -1):
                    if s[t]:
                        nxt += 1
                    else:
                        nxt = 0
                    rl[t] = nxt
                self._runlen.append(rl)

            # any_spot, best_region, best_runlen
            for t in range(self._N):
                br = -1
                bl = 0
                anyv = 0
                for r in range(self._num_regions):
                    if self._spot[r][t]:
                        anyv = 1
                        v = self._runlen[r][t]
                        if v > bl:
                            bl = v
                            br = r
                self._any_spot[t] = anyv
                self._best_region[t] = br
                self._best_runlen[t] = bl

            # future any spot capacity
            acc = 0
            for t in range(self._N - 1, -1, -1):
                acc += 1 if self._any_spot[t] else 0
                self._future_any_spot[t] = acc

            # next spot per region (steps until next spot)
            BIG = self._N + 10
            self._BIG = BIG
            for r in range(self._num_regions):
                ns = array("I", [BIG] * self._N)
                s = self._spot[r]
                next_idx = BIG
                for t in range(self._N - 1, -1, -1):
                    if s[t]:
                        next_idx = t
                    ns[t] = (next_idx - t) if next_idx != BIG else BIG
                self._next_spot.append(ns)

        except Exception:
            self._use_traces = False

        self._urgent_buffer = max(2.0 * self._restart_overhead, 4.0 * self._gap)
        self._idle_min_slack = max(self._restart_overhead + self._gap, 3.0 * self._gap)
        self._need_margin = max(3.0 * self._restart_overhead, 2.0 * self._gap)

        return self

    def _update_done_work(self) -> None:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            return
        n = len(lst)
        i = self._done_len
        if i >= n:
            return
        s = 0.0
        while i < n:
            s += float(lst[i])
            i += 1
        self._done_work += s
        self._done_len = n

    def _align_index(self, base_idx: int, has_spot: bool) -> int:
        if not self._use_traces:
            return base_idx
        cur = int(self.env.get_current_region()) if hasattr(self.env, "get_current_region") else 0
        if cur < 0 or cur >= self._num_regions:
            return base_idx
        # Try current offset
        idx = base_idx + self._trace_offset
        if 0 <= idx < self._N:
            pred = bool(self._spot[cur][idx])
            if pred == bool(has_spot):
                self._mismatch = 0
                return idx
        # Try small offsets
        found = None
        for off in (0, -1, 1, -2, 2, -3, 3):
            j = base_idx + off
            if 0 <= j < self._N:
                if bool(self._spot[cur][j]) == bool(has_spot):
                    found = off
                    idx = j
                    break
        if found is not None:
            self._trace_offset = found
            self._mismatch = 0
            return idx
        self._mismatch += 1
        if self._mismatch >= 8:
            self._use_traces = False
        return base_idx

    def _maybe_switch_for_next(self, idx: int) -> None:
        if not self._use_traces:
            return
        j = idx + 1
        if j < 0 or j >= self._N:
            return
        cur = int(self.env.get_current_region()) if hasattr(self.env, "get_current_region") else 0

        r = int(self._best_region[j]) if self._any_spot[j] else -1
        if r < 0:
            # Choose soonest next spot
            best_r = cur
            best_w = self._BIG
            for rr in range(self._num_regions):
                w = int(self._next_spot[rr][j])
                if w < best_w:
                    best_w = w
                    best_r = rr
            if best_w >= self._BIG:
                return
            r = best_r

        if r != cur and hasattr(self.env, "switch_region"):
            try:
                self.env.switch_region(int(r))
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_work()

        td = self._task_duration
        remaining_work = td - self._done_work
        if remaining_work <= 0:
            return _CT_NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline - elapsed

        rro = float(getattr(self, "remaining_restart_overhead", 0.0))
        if rro < 0:
            rro = 0.0

        # If too close to deadline, lock to on-demand to avoid interruption cascades.
        if not self._lock_on_demand:
            need = remaining_work + rro + self._need_margin
            if time_left <= need + self._urgent_buffer:
                self._lock_on_demand = True

        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        base_idx = int(elapsed / self._gap + 1e-9) if self._gap > 0 else 0
        idx = self._align_index(base_idx, bool(has_spot))

        # Use SPOT only if current step has spot in the current region (as per API contract).
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region this step. Decide NONE vs ON_DEMAND.
        slack = time_left - (remaining_work + rro)
        spot_capacity = -1e30
        if self._use_traces and 0 <= idx < self._N:
            # Upper bound: steps where any region has spot available.
            spot_capacity = float(self._future_any_spot[idx]) * self._gap - 3.0 * self._restart_overhead

        choose_none = False
        if spot_capacity >= remaining_work and slack >= self._idle_min_slack:
            choose_none = True
        elif not self._use_traces and slack >= max(8.0 * self._gap, self._idle_min_slack):
            choose_none = True

        if choose_none:
            self._maybe_switch_for_next(idx)
            return _CT_NONE

        self._maybe_switch_for_next(idx)
        return ClusterType.ON_DEMAND