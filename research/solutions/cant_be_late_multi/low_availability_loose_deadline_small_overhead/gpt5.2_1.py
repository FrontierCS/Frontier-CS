import json
import os
import math
import pickle
from argparse import Namespace
from typing import Any, Callable, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_ONDEMAND = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None")


def _as_bool_array(x: Any) -> Any:
    if np is None:
        if isinstance(x, (bytes, bytearray)):
            return [1 if b else 0 for b in x]
        if isinstance(x, (list, tuple)):
            return [1 if bool(v) else 0 for v in x]
        return [1 if bool(v) else 0 for v in list(x)]

    arr = np.asarray(x)
    if arr.dtype == np.bool_:
        return arr
    if arr.dtype.kind in ("i", "u", "b"):
        return (arr != 0)
    if arr.dtype.kind == "f":
        return (arr > 0.5)
    if arr.dtype.kind in ("U", "S", "O"):
        flat = arr.reshape(-1)
        out = np.empty(flat.shape[0], dtype=np.bool_)
        for i, v in enumerate(flat.tolist()):
            if isinstance(v, (bool, np.bool_)):
                out[i] = bool(v)
            elif isinstance(v, (int, float)):
                out[i] = v > 0.5
            else:
                s = str(v).strip().lower()
                if s in ("1", "true", "t", "yes", "y"):
                    out[i] = True
                else:
                    out[i] = False
        return out.reshape(arr.shape)
    return (arr.astype(np.float32) > 0.5)


def _load_trace_file(path: str) -> Sequence[int]:
    ext = os.path.splitext(path)[1].lower()
    if np is not None and ext == ".npy":
        arr = np.load(path, allow_pickle=True)
        arr = _as_bool_array(arr).reshape(-1)
        return arr.astype(np.uint8).tolist()
    if np is not None and ext == ".npz":
        z = np.load(path, allow_pickle=True)
        key = list(z.files)[0]
        arr = _as_bool_array(z[key]).reshape(-1)
        return arr.astype(np.uint8).tolist()
    if ext in (".pkl", ".pickle"):
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if isinstance(obj, dict):
            for k in ("availability", "avail", "trace", "data", "spot"):
                if k in obj:
                    obj = obj[k]
                    break
        if np is not None:
            arr = _as_bool_array(obj).reshape(-1)
            return arr.astype(np.uint8).tolist()
        return [1 if bool(v) else 0 for v in obj]

    # text / json
    with open(path, "r", encoding="utf-8") as f:
        # peek first non-ws char
        pos = f.tell()
        ch = f.read(1)
        while ch and ch.isspace():
            ch = f.read(1)
        f.seek(pos)
        if ch in ("[", "{"):
            obj = json.load(f)
            if isinstance(obj, dict):
                for k in ("availability", "avail", "trace", "data", "spot"):
                    if k in obj:
                        obj = obj[k]
                        break
            if np is not None:
                arr = _as_bool_array(obj).reshape(-1)
                return arr.astype(np.uint8).tolist()
            return [1 if bool(v) else 0 for v in obj]

        vals: List[int] = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            c0 = line[0]
            if not (c0.isdigit() or c0 in "+-."):
                # likely header
                continue
            if "," in line:
                toks = line.split(",")
            else:
                toks = line.split()
            if not toks:
                continue
            s = toks[-1].strip()
            sl = s.lower()
            if sl in ("1", "true", "t", "yes", "y"):
                vals.append(1)
            elif sl in ("0", "false", "f", "no", "n"):
                vals.append(0)
            else:
                try:
                    v = float(s)
                    vals.append(1 if v > 0.5 else 0)
                except Exception:
                    continue
        return vals


def _compute_next_true(arr_bool: Any) -> Any:
    # arr_bool: bool array length T
    T = int(len(arr_bool))
    if np is not None:
        out = np.empty(T + 1, dtype=np.int32)
    else:
        out = [0] * (T + 1)

    nxt = T
    for i in range(T - 1, -1, -1):
        if bool(arr_bool[i]):
            nxt = i
        if np is not None:
            out[i] = nxt
        else:
            out[i] = nxt
    if np is not None:
        out[T] = T
    else:
        out[T] = T
    return out


def _compute_next_false(arr_bool: Any) -> Any:
    T = int(len(arr_bool))
    if np is not None:
        out = np.empty(T + 1, dtype=np.int32)
    else:
        out = [0] * (T + 1)

    nxt = T
    for i in range(T - 1, -1, -1):
        if not bool(arr_bool[i]):
            nxt = i
        if np is not None:
            out[i] = nxt
        else:
            out[i] = nxt
    if np is not None:
        out[T] = T
    else:
        out[T] = T
    return out


class Solution(MultiRegionStrategy):
    NAME = "spot_oracle_multi_v2"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        trace_files = config.get("trace_files", [])
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
            trace_files=trace_files,
            trace_paths=trace_files,
            spot_trace_paths=trace_files,
        )
        super().__init__(args)

        self._trace_files: List[str] = list(trace_files) if trace_files is not None else []
        self._initialized_policy = False

        self._last_task_done_len = 0
        self._work_done = 0.0
        self._sticky_ondemand = False
        self._last_elapsed = -1.0

        self._num_regions = 0
        self._gap = 0.0
        self._inv_gap = 0.0
        self._horizon_steps = 0

        self._spot_traces = None
        self._any_spot = None
        self._next_any_spot = None
        self._next_unavail = None  # list of next_false arrays per region

        self._stick_slack_threshold = 0.0
        self._switch_back_slack_threshold = 0.0
        self._min_run_steps_to_switch = 1

        return self

    def _reset_episode_state(self) -> None:
        self._last_task_done_len = 0
        self._work_done = 0.0
        self._sticky_ondemand = False

    def _update_work_done(self) -> None:
        td = self.task_done_time
        n = len(td)
        i = self._last_task_done_len
        if n > i:
            acc = self._work_done
            for j in range(i, n):
                acc += float(td[j])
            self._work_done = acc
            self._last_task_done_len = n

    def _ensure_initialized(self) -> None:
        if self._initialized_policy:
            return

        self._num_regions = int(self.env.get_num_regions())
        self._gap = float(self.env.gap_seconds)
        if self._gap <= 0:
            self._gap = 1.0
        self._inv_gap = 1.0 / self._gap

        self._horizon_steps = int(math.ceil(float(self.deadline) / self._gap)) + 3
        if self._horizon_steps < 10:
            self._horizon_steps = 10

        # Adaptive thresholds (seconds)
        over = float(self.restart_overhead)
        gap = self._gap
        self._stick_slack_threshold = max(6.0 * over + 2.0 * gap, 2.0 * over)
        self._switch_back_slack_threshold = max(8.0 * over + 2.0 * gap, 3.0 * over)
        self._min_run_steps_to_switch = max(1, int(math.ceil(over / gap)) + 2)

        # Load traces for all regions
        traces: List[Sequence[int]] = []
        tf = self._trace_files[: self._num_regions]
        for r in range(self._num_regions):
            if r < len(tf) and tf[r]:
                try:
                    seq = _load_trace_file(tf[r])
                except Exception:
                    seq = []
            else:
                seq = []
            if not seq:
                # Fallback: assume no spot if missing
                seq = [0] * self._horizon_steps
            traces.append(seq)

        # Normalize lengths (tile or truncate)
        norm_traces = []
        for seq in traces:
            n = len(seq)
            if n <= 0:
                norm_traces.append([0] * self._horizon_steps)
                continue
            if n < self._horizon_steps:
                rep = (self._horizon_steps + n - 1) // n
                tiled = (list(seq) * rep)[: self._horizon_steps]
                norm_traces.append(tiled)
            else:
                norm_traces.append(list(seq[: self._horizon_steps]))

        if np is not None:
            self._spot_traces = [np.asarray(t, dtype=np.uint8) != 0 for t in norm_traces]
            any_spot = self._spot_traces[0].copy()
            for r in range(1, self._num_regions):
                any_spot |= self._spot_traces[r]
            self._any_spot = any_spot
        else:
            self._spot_traces = [[1 if v else 0 for v in t] for t in norm_traces]
            any_spot = [0] * self._horizon_steps
            for i in range(self._horizon_steps):
                v = 0
                for r in range(self._num_regions):
                    if self._spot_traces[r][i]:
                        v = 1
                        break
                any_spot[i] = v
            self._any_spot = any_spot

        self._next_any_spot = _compute_next_true(self._any_spot)
        self._next_unavail = [_compute_next_false(self._spot_traces[r]) for r in range(self._num_regions)]

        self._initialized_policy = True

    def _spot_available(self, region: int, step_idx: int) -> bool:
        if step_idx < 0:
            step_idx = 0
        if step_idx >= self._horizon_steps:
            step_idx = self._horizon_steps - 1
        tr = self._spot_traces[region]
        return bool(tr[step_idx])

    def _select_best_spot_region(self, step_idx: int, prefer: int) -> Optional[int]:
        best_r = -1
        best_run = -1

        for r in range(self._num_regions):
            if not self._spot_available(r, step_idx):
                continue
            nxt0 = self._next_unavail[r][step_idx]
            run = int(nxt0 - step_idx)
            if run > best_run:
                best_run = run
                best_r = r
            elif run == best_run and r == prefer:
                best_r = r

        if best_r < 0:
            return None
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        elapsed = float(self.env.elapsed_seconds)
        if self._last_elapsed >= 0.0 and elapsed + 1e-9 < self._last_elapsed:
            self._reset_episode_state()
        self._last_elapsed = elapsed

        self._update_work_done()
        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 1e-9:
            return _CT_NONE

        time_remaining = float(self.deadline) - elapsed
        if time_remaining <= 1e-9:
            return _CT_NONE

        rem_over = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        slack_eff = time_remaining - remaining_work - rem_over

        # If restart overhead is still pending, avoid causing new restarts.
        if rem_over > 1e-9:
            if last_cluster_type == _CT_SPOT:
                if has_spot:
                    return _CT_SPOT
                return _CT_ONDEMAND
            if last_cluster_type == _CT_ONDEMAND:
                return _CT_ONDEMAND
            return _CT_NONE

        # If extremely tight, commit to on-demand.
        # Also commit when required utilization is close to 1 (can't afford extra restarts/waits).
        denom = max(1e-9, time_remaining)
        required_rate = remaining_work / denom
        if self._sticky_ondemand or slack_eff <= self._stick_slack_threshold or required_rate >= 0.985:
            self._sticky_ondemand = True
            return _CT_ONDEMAND

        step_idx = int(elapsed * self._inv_gap + 1e-9)
        if step_idx < 0:
            step_idx = 0
        if step_idx >= self._horizon_steps:
            step_idx = self._horizon_steps - 1

        any_spot_now = bool(self._any_spot[step_idx])

        if any_spot_now:
            current_region = int(self.env.get_current_region())

            # If we're already on spot and it's available here, keep it to avoid restarts.
            if last_cluster_type == _CT_SPOT and has_spot:
                return _CT_SPOT

            # If currently on on-demand and slack is low, don't switch back (restart overhead risk).
            if last_cluster_type == _CT_ONDEMAND and slack_eff <= self._switch_back_slack_threshold:
                return _CT_ONDEMAND

            best_region = self._select_best_spot_region(step_idx, prefer=current_region)
            if best_region is not None and best_region != current_region:
                self.env.switch_region(best_region)

            # Only switch to spot if it is expected to last long enough to amortize restart overhead
            if best_region is not None:
                run_steps = int(self._next_unavail[best_region][step_idx] - step_idx)
                if last_cluster_type == _CT_ONDEMAND and run_steps < self._min_run_steps_to_switch:
                    return _CT_ONDEMAND
            return _CT_SPOT

        # No spot anywhere now
        next_spot = int(self._next_any_spot[step_idx])
        if next_spot >= self._horizon_steps:
            self._sticky_ondemand = True
            return _CT_ONDEMAND

        wait_steps = next_spot - step_idx
        wait_time = float(wait_steps) * self._gap

        # If we can wait until next spot without jeopardizing the deadline, pause.
        if slack_eff >= wait_time + float(self.restart_overhead):
            return _CT_NONE

        # Otherwise, run on-demand; become sticky if getting tight.
        if slack_eff <= 2.0 * self._stick_slack_threshold:
            self._sticky_ondemand = True
        return _CT_ONDEMAND