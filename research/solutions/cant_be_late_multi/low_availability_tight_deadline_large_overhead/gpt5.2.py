import json
import os
import math
from argparse import Namespace
from array import array
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def _read_trace_file(path: str) -> Optional[bytearray]:
    if path is None:
        return None
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".npy", ".npz"):
            try:
                import numpy as np  # type: ignore
            except Exception:
                np = None
            if np is not None:
                if ext == ".npy":
                    arr = np.load(path, allow_pickle=False)
                else:
                    z = np.load(path, allow_pickle=False)
                    key = None
                    if hasattr(z, "files") and z.files:
                        key = z.files[0]
                    if key is None:
                        return None
                    arr = z[key]
                arr = arr.reshape(-1)
                if arr.dtype == np.bool_:
                    return bytearray(arr.astype(np.uint8).tolist())
                if np.issubdtype(arr.dtype, np.number):
                    return bytearray((arr > 0).astype(np.uint8).tolist())
                try:
                    return bytearray((bool(x) for x in arr.tolist()))
                except Exception:
                    return None

        with open(path, "rb") as f:
            head = f.read(4096)
        head_stripped = head.lstrip()
        if head_stripped.startswith(b"[") or head_stripped.startswith(b"{"):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                for k in ("trace", "availability", "has_spot", "data", "values"):
                    if k in obj:
                        obj = obj[k]
                        break
            if not isinstance(obj, list):
                return None
            out = bytearray()
            append = out.append
            for x in obj:
                v = 0
                if isinstance(x, (list, tuple)) and x:
                    x = x[-1]
                if isinstance(x, bool):
                    v = 1 if x else 0
                elif isinstance(x, (int, float)):
                    v = 1 if x > 0 else 0
                elif isinstance(x, str):
                    s = x.strip().lower()
                    if not s:
                        continue
                    c = s[0]
                    if c in ("1", "t", "y"):
                        v = 1
                    elif c in ("0", "f", "n"):
                        v = 0
                    else:
                        v = 1 if _safe_float(s) > 0 else 0
                else:
                    v = 1 if bool(x) else 0
                append(v)
            return out

        out = bytearray()
        append = out.append
        with open(path, "rb") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(b"#"):
                    continue
                if b"," in line:
                    tok = line.rsplit(b",", 1)[-1].strip()
                else:
                    parts = line.split()
                    if not parts:
                        continue
                    tok = parts[-1]
                if not tok:
                    continue
                c = tok[:1]
                if c in (b"1", b"t", b"T", b"y", b"Y"):
                    append(1)
                elif c in (b"0", b"f", b"F", b"n", b"N"):
                    append(0)
                else:
                    try:
                        append(1 if float(tok.decode("utf-8", "ignore")) > 0.0 else 0)
                    except Exception:
                        # Best effort: treat unknown token as unavailable.
                        append(0)
        return out
    except Exception:
        return None


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

        self._trace_files = list(config.get("trace_files", []) or [])
        self._raw_traces: List[Optional[bytearray]] = []
        for p in self._trace_files:
            self._raw_traces.append(_read_trace_file(p))

        self._setup_done = False
        self._use_traces = any(t is not None and len(t) > 0 for t in self._raw_traces)

        self._avail: List[bytearray] = []
        self._streaks: List[array] = []
        self._next_on: List[array] = []
        self._best_region: array = array("h")
        self._best_len: array = array("I")

        self._gap = None
        self._horizon_steps = 0
        self._overhead_steps = 1
        self._commit = False

        self._done_sum = 0.0
        self._done_len = 0

        self._last_checked_idx = -1
        self._trace_consistent = True

        return self

    def _time_index(self) -> int:
        g = self.env.gap_seconds
        if g <= 0:
            return 0
        return int(self.env.elapsed_seconds // g)

    def _update_done_sum(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n != self._done_len:
            self._done_sum += sum(td[self._done_len : n])
            self._done_len = n
        return self._done_sum

    def _env_current_has_spot(self) -> Optional[bool]:
        e = self.env
        for name in ("has_spot", "spot_available", "spot_availability", "current_has_spot"):
            try:
                v = getattr(e, name)
            except Exception:
                continue
            if isinstance(v, bool):
                return v
        for m in ("get_has_spot", "get_spot", "is_spot_available", "has_spot_available"):
            fn = getattr(e, m, None)
            if fn is None or not callable(fn):
                continue
            try:
                v = fn()
            except Exception:
                continue
            if isinstance(v, bool):
                return v
        return None

    def _setup_if_needed(self) -> None:
        if self._setup_done:
            return

        self._gap = float(self.env.gap_seconds)
        if self._gap <= 0:
            self._gap = 1.0
        self._horizon_steps = int(math.ceil(float(self.deadline) / self._gap)) + 3

        try:
            n_regions = int(self.env.get_num_regions())
        except Exception:
            n_regions = len(self._raw_traces) if self._raw_traces else 1
        if n_regions <= 0:
            n_regions = 1

        if not self._use_traces or not self._raw_traces:
            self._use_traces = False
            self._setup_done = True
            return

        traces = self._raw_traces[:n_regions]
        if len(traces) < n_regions:
            traces = traces + [None] * (n_regions - len(traces))

        self._avail = []
        for r in range(n_regions):
            raw = traces[r]
            if raw is None or len(raw) == 0:
                a = bytearray(self._horizon_steps)
            else:
                if len(raw) >= self._horizon_steps:
                    a = bytearray(raw[: self._horizon_steps])
                else:
                    a = bytearray(raw)
                    a.extend(b"\x00" * (self._horizon_steps - len(a)))
            self._avail.append(a)

        self._overhead_steps = max(1, int(math.ceil(float(self.restart_overhead) / self._gap)))

        self._streaks = []
        self._next_on = []
        T = self._horizon_steps
        for r in range(n_regions):
            a = self._avail[r]
            st = array("I", [0]) * T
            no = array("I", [0]) * T
            run = 0
            nxt = T
            for i in range(T - 1, -1, -1):
                if a[i]:
                    run += 1
                    nxt = i
                else:
                    run = 0
                st[i] = run
                no[i] = nxt
            self._streaks.append(st)
            self._next_on.append(no)

        best_r = array("h", [-1]) * T
        best_l = array("I", [0]) * T
        for i in range(T):
            br = -1
            bl = 0
            for r in range(n_regions):
                if self._avail[r][i]:
                    l = self._streaks[r][i]
                    if l > bl:
                        bl = l
                        br = r
            best_r[i] = br
            best_l[i] = bl
        self._best_region = best_r
        self._best_len = best_l

        self._setup_done = True

    def _should_commit_on_demand(self, slack_left: float, remaining_time: float, remaining_work: float) -> bool:
        if self._commit:
            return True
        g = float(self.env.gap_seconds)
        if remaining_work <= 0:
            return False
        # Conservative: commit when slack is small enough that another restart/outage could cause failure.
        thresh = float(self.restart_overhead) + 0.5 * g
        if slack_left <= thresh:
            return True
        if remaining_time <= remaining_work + float(self.restart_overhead):
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._setup_if_needed()

        work_done = self._update_done_sum()
        remaining_work = float(self.task_duration) - float(work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        slack_left = remaining_time - remaining_work

        if self._should_commit_on_demand(slack_left, remaining_time, remaining_work):
            self._commit = True

        if not self._use_traces or not self._setup_done or not self._avail:
            if self._commit:
                return ClusterType.ON_DEMAND
            if has_spot:
                return ClusterType.SPOT
            if slack_left >= float(self.env.gap_seconds):
                return ClusterType.NONE
            self._commit = True
            return ClusterType.ON_DEMAND

        idx = self._time_index()
        if idx < 0:
            idx = 0
        if idx >= self._horizon_steps:
            idx = self._horizon_steps - 1

        # Consistency check (disable traces if they don't align with observed has_spot in current region).
        if self._trace_consistent and idx != self._last_checked_idx:
            self._last_checked_idx = idx
            try:
                cur0 = int(self.env.get_current_region())
            except Exception:
                cur0 = 0
            if 0 <= cur0 < len(self._avail):
                pred0 = bool(self._avail[cur0][idx])
                if pred0 != bool(has_spot):
                    self._trace_consistent = False
                    self._use_traces = False
                    if self._commit:
                        return ClusterType.ON_DEMAND
                    if has_spot:
                        return ClusterType.SPOT
                    if slack_left >= float(self.env.gap_seconds):
                        return ClusterType.NONE
                    self._commit = True
                    return ClusterType.ON_DEMAND

        if self._commit:
            return ClusterType.ON_DEMAND

        # Avoid switching while overhead is pending.
        if float(self.remaining_restart_overhead) <= 1e-9:
            try:
                cur = int(self.env.get_current_region())
            except Exception:
                cur = 0
            if not (0 <= cur < len(self._avail)):
                cur = 0

            best = int(self._best_region[idx]) if idx < len(self._best_region) else -1
            if best != -1 and best != cur:
                cur_avail = bool(self._avail[cur][idx])
                cur_len = int(self._streaks[cur][idx]) if cur_avail else 0
                best_len = int(self._best_len[idx]) if idx < len(self._best_len) else 0

                # If current region is down, consider switching if we'd otherwise wait longer than restart overhead.
                if not cur_avail:
                    nxt = int(self._next_on[cur][idx])
                    down_steps = (nxt - idx) if nxt < self._horizon_steps else self._horizon_steps
                    if down_steps >= self._overhead_steps + 1 and slack_left > float(self.restart_overhead):
                        self.env.switch_region(best)
                        cur = best
                else:
                    # Preemptive switch only if it buys enough uninterrupted availability to amortize overhead.
                    if best_len >= max(self._overhead_steps + 1, cur_len + self._overhead_steps) and slack_left > float(self.restart_overhead):
                        self.env.switch_region(best)
                        cur = best

        # Decide cluster type in current region.
        env_spot = self._env_current_has_spot()
        if env_spot is None:
            try:
                cur = int(self.env.get_current_region())
            except Exception:
                cur = 0
            if 0 <= cur < len(self._avail):
                env_spot = bool(self._avail[cur][idx])
            else:
                env_spot = bool(has_spot)

        if env_spot:
            return ClusterType.SPOT

        if slack_left >= float(self.env.gap_seconds):
            return ClusterType.NONE

        self._commit = True
        return ClusterType.ON_DEMAND