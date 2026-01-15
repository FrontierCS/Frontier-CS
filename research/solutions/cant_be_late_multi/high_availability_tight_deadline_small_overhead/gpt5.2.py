import json
import math
import gzip
from argparse import Namespace
from array import array
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_bool_token(tok: str) -> Optional[bool]:
    s = tok.strip().lower()
    if not s:
        return None
    if s in ("1", "true", "t", "yes", "y", "available", "avail", "up"):
        return True
    if s in ("0", "false", "f", "no", "n", "unavailable", "down", "na", "nan", "none", "null"):
        return False
    try:
        v = float(s)
    except Exception:
        return None
    if v == 0.0:
        return False
    if v == 1.0:
        return True
    if math.isnan(v):
        return False
    # If a numeric value is not 0/1, we cannot reliably interpret it.
    # Return None so the parser may try a different column.
    return None


def _extract_bool_from_obj(obj: Any) -> Optional[bool]:
    if isinstance(obj, bool):
        return obj
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        if obj == 0 or obj == 0.0:
            return False
        if obj == 1 or obj == 1.0:
            return True
        if isinstance(obj, float) and math.isnan(obj):
            return False
        return None
    if isinstance(obj, str):
        return _to_bool_token(obj)
    return None


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_deadline_guard"

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

        self._trace_files: List[str] = list(config.get("trace_files", []))
        self._has_traces: bool = False
        self._avail: List[bytearray] = []
        self._run_len: List[array] = []
        self._next_true: List[array] = []
        self._any_spot_suffix: Optional[array] = None
        self._trace_len: int = 0

        self._done_sum: float = 0.0
        self._done_len: int = 0

        self._committed_on_demand: bool = False
        self._commit_buffer_seconds: float = 0.0
        self._finish_buffer_seconds: float = 0.0

        self._last_switch_step: int = -10**18
        self._switch_cooldown_steps: int = 1

        self._init_traces()
        self._init_buffers()
        return self

    def _scalar(self, x: Any) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _init_buffers(self) -> None:
        deadline = self._scalar(getattr(self, "deadline", 0.0))
        duration = self._scalar(getattr(self, "task_duration", 0.0))
        slack_total = max(0.0, deadline - duration)

        # Commit buffer: aim to have ample slack to safely switch to on-demand and finish.
        # Bound it to avoid overly aggressive on-demand usage.
        commit_buf = 0.15 * slack_total
        commit_buf = max(1800.0, min(7200.0, commit_buf))
        self._commit_buffer_seconds = commit_buf

        # Finish buffer: guard for discrete steps / bookkeeping.
        ro = self._scalar(getattr(self, "restart_overhead", 0.0))
        self._finish_buffer_seconds = max(60.0, ro)  # refined once env.gap_seconds is known

    def _open_maybe_gzip(self, path: str):
        if path.endswith(".gz"):
            return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
        return open(path, "rt", encoding="utf-8", errors="ignore")

    def _parse_trace_file(self, path: str) -> Optional[bytearray]:
        try:
            with self._open_maybe_gzip(path) as f:
                # Peek first non-empty, non-comment content
                head_lines = []
                for _ in range(50):
                    line = f.readline()
                    if not line:
                        break
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    head_lines.append(s)
                    if len(head_lines) >= 3:
                        break
                if not head_lines:
                    return bytearray()

            first = head_lines[0]
            if first[0] in "[{":
                with self._open_maybe_gzip(path) as f:
                    data = json.load(f)
                return self._parse_trace_json(data)

            # Otherwise, treat as text/csv-like
            return self._parse_trace_text(path)
        except Exception:
            return None

    def _parse_trace_json(self, data: Any) -> Optional[bytearray]:
        seq = None
        if isinstance(data, dict):
            # Try common keys
            for k in ("availability", "avail", "spot", "has_spot", "trace", "data", "values"):
                if k in data and isinstance(data[k], (list, tuple)):
                    seq = data[k]
                    break
            if seq is None:
                # If dict of idx->val
                try:
                    items = sorted(data.items(), key=lambda kv: int(kv[0]))
                    seq = [v for _, v in items]
                except Exception:
                    return None
        elif isinstance(data, (list, tuple)):
            seq = data
        else:
            return None

        out = bytearray()
        for item in seq:
            b = _extract_bool_from_obj(item)
            if b is None and isinstance(item, dict):
                for k in ("available", "avail", "has_spot", "spot", "value", "v"):
                    if k in item:
                        b = _extract_bool_from_obj(item[k])
                        if b is not None:
                            break
            if b is None:
                # If numeric but not 0/1, assume True is unsafe; treat as None => False.
                b = False
            out.append(1 if b else 0)
        return out

    def _parse_trace_text(self, path: str) -> Optional[bytearray]:
        out = bytearray()
        try:
            with self._open_maybe_gzip(path) as f:
                header = None
                header_cols = None
                data_started = False
                col_idx = None

                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    # Detect header
                    if not data_started:
                        # If line contains alphabetic, treat as header row.
                        if any(("a" <= ch.lower() <= "z") for ch in s):
                            header = s
                            header_cols = [c.strip().lower() for c in s.replace("\t", ",").split(",")]
                            for i, col in enumerate(header_cols):
                                if "avail" in col or "has_spot" in col or col in ("spot", "available"):
                                    col_idx = i
                                    break
                            continue
                        data_started = True

                    parts = s.replace("\t", ",").split(",") if "," in s else s.split()
                    if not parts:
                        continue

                    candidates = []
                    if col_idx is not None and col_idx < len(parts):
                        candidates.append(parts[col_idx])
                    candidates.append(parts[-1])
                    if len(parts) >= 2:
                        candidates.append(parts[1])
                        candidates.append(parts[0])

                    bval = None
                    for tok in candidates:
                        bval = _to_bool_token(tok)
                        if bval is not None:
                            break
                    if bval is None:
                        # Try interpret as 0/1 from any column
                        for tok in parts:
                            bval = _to_bool_token(tok)
                            if bval is not None:
                                break
                    if bval is None:
                        # Unrecognized row; skip
                        continue
                    out.append(1 if bval else 0)
            return out
        except Exception:
            return None

    def _init_traces(self) -> None:
        if not self._trace_files:
            self._has_traces = False
            return
        traces: List[bytearray] = []
        for p in self._trace_files:
            arr = self._parse_trace_file(p)
            if arr is None or len(arr) == 0:
                traces.append(bytearray())
            else:
                traces.append(arr)

        max_len = max((len(t) for t in traces), default=0)
        if max_len <= 0:
            self._has_traces = False
            return

        # Pad all traces to max_len with 0 (unavailable).
        padded: List[bytearray] = []
        for t in traces:
            if len(t) < max_len:
                tt = bytearray(t)
                tt.extend(b"\x00" * (max_len - len(tt)))
                padded.append(tt)
            else:
                padded.append(t)

        self._avail = padded
        self._trace_len = max_len
        self._has_traces = True

        # Precompute run_len and next_true for each region.
        self._run_len = []
        self._next_true = []
        for t in self._avail:
            rl = array("I", [0]) * max_len
            nt = array("I", [0]) * max_len

            next_idx = 2**31 - 1
            run = 0
            for i in range(max_len - 1, -1, -1):
                if t[i]:
                    run += 1
                    rl[i] = run
                    next_idx = i
                else:
                    run = 0
                    rl[i] = 0
                nt[i] = next_idx
            self._run_len.append(rl)
            self._next_true.append(nt)

        # any-spot suffix count (upper bound of future spot steps)
        any_spot = bytearray(max_len)
        for i in range(max_len):
            v = 0
            for r in range(len(self._avail)):
                if self._avail[r][i]:
                    v = 1
                    break
            any_spot[i] = v

        suffix = array("I", [0]) * (max_len + 1)
        acc = 0
        for i in range(max_len - 1, -1, -1):
            acc += 1 if any_spot[i] else 0
            suffix[i] = acc
        self._any_spot_suffix = suffix

    def _update_done_sum(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            self._done_sum = 0.0
            self._done_len = 0
            return 0.0
        ln = len(tdt)
        if ln < self._done_len:
            self._done_sum = float(sum(tdt))
            self._done_len = ln
            return self._done_sum
        if ln > self._done_len:
            # Incremental update
            s = 0.0
            for i in range(self._done_len, ln):
                s += float(tdt[i])
            self._done_sum += s
            self._done_len = ln
        return self._done_sum

    def _idx_step(self) -> int:
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0
        return int(float(getattr(self.env, "elapsed_seconds", 0.0)) / gap)

    def _ensure_runtime_params(self) -> None:
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0
        ro = self._scalar(getattr(self, "restart_overhead", 0.0))
        self._switch_cooldown_steps = max(1, int(math.ceil(ro / gap)))
        self._finish_buffer_seconds = max(self._finish_buffer_seconds, 3.0 * gap + ro)

    def _can_switch(self, idx: int) -> bool:
        return (idx - self._last_switch_step) >= self._switch_cooldown_steps

    def _best_region_with_spot_at(self, idx: int, n: int) -> Optional[int]:
        if not self._has_traces or idx < 0 or idx >= self._trace_len:
            return None
        best_r = None
        best_run = -1
        for r in range(min(n, len(self._avail))):
            if self._avail[r][idx]:
                run = int(self._run_len[r][idx])
                if run > best_run:
                    best_run = run
                    best_r = r
        return best_r

    def _earliest_region_next_spot(self, idx: int, n: int) -> Optional[int]:
        if not self._has_traces or idx < 0 or idx >= self._trace_len:
            return None
        best_r = None
        best_next = 2**31 - 1
        for r in range(min(n, len(self._avail))):
            nxt = int(self._next_true[r][idx])
            if nxt < best_next:
                best_next = nxt
                best_r = r
        if best_next >= 2**31 - 2:
            return None
        return best_r

    def _maybe_switch_region(self, idx: int, has_spot: bool) -> None:
        n = int(self.env.get_num_regions())
        if n <= 1:
            return
        cur = int(self.env.get_current_region())
        if not self._can_switch(idx):
            return

        if self._has_traces:
            # Safe switching behavior: if we plan to run SPOT this step (has_spot True),
            # only switch to a region that also has spot at this step (to be safe under both
            # "immediate" and "next-step" switching semantics).
            if has_spot:
                best_now = self._best_region_with_spot_at(idx, n)
                if best_now is not None and best_now != cur:
                    # Only switch if destination also has spot now (guaranteed by best_now),
                    # and significantly longer run to justify.
                    run_cur = int(self._run_len[cur][idx]) if cur < len(self._run_len) else 0
                    run_best = int(self._run_len[best_now][idx])
                    if run_best > run_cur + max(2, self._switch_cooldown_steps):
                        self.env.switch_region(best_now)
                        self._last_switch_step = idx
                return

            # has_spot is False: switch to a region with spot now if possible, else earliest next spot.
            best_now = self._best_region_with_spot_at(idx, n)
            target = best_now
            if target is None:
                target = self._earliest_region_next_spot(idx, n)
            if target is not None and target != cur:
                self.env.switch_region(target)
                self._last_switch_step = idx
            return

        # No traces: simple probing hop when spot is unavailable.
        if not has_spot:
            target = (cur + 1) % n
            self.env.switch_region(target)
            self._last_switch_step = idx

    def _should_commit_on_demand(self, idx: int, last_cluster_type: ClusterType, work_left: float) -> bool:
        deadline = self._scalar(getattr(self, "deadline", 0.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = deadline - elapsed

        if work_left <= 0.0:
            return False
        if time_left <= 0.0:
            return True

        ro = self._scalar(getattr(self, "restart_overhead", 0.0))
        overhead_commit = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro

        # Feasibility guard (deterministic): if switching to on-demand now is needed to safely finish.
        if time_left <= work_left + overhead_commit + self._finish_buffer_seconds + self._commit_buffer_seconds:
            return True

        # If we have trace data, check optimistic future spot capacity (across all regions).
        # If even an optimistic bound cannot cover remaining work, commit.
        if self._any_spot_suffix is not None:
            gap = float(getattr(self.env, "gap_seconds", 1.0))
            if gap <= 0:
                gap = 1.0
            if 0 <= idx < self._trace_len:
                max_spot_steps = int(self._any_spot_suffix[idx])
                max_spot_work = max_spot_steps * gap
                # Conservative margin for restarts / switching overheads.
                # Keep small to not overuse on-demand, but nonzero for safety.
                margin = max(0.0, 10.0 * ro)
                if max_spot_work + margin < work_left:
                    return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_runtime_params()

        done = self._update_done_sum()
        task_duration = self._scalar(getattr(self, "task_duration", 0.0))
        work_left = max(0.0, task_duration - done)
        if work_left <= 0.0:
            return ClusterType.NONE

        idx = self._idx_step()

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        if self._should_commit_on_demand(idx, last_cluster_type, work_left):
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        self._maybe_switch_region(idx, has_spot)

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE