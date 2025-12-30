import os
import re
import csv
import math
import json
import gzip
from array import array
from argparse import Namespace
from typing import List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_text_maybe_gzip(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore", newline="")
    return open(path, "rt", encoding="utf-8", errors="ignore", newline="")


def _to_bool_token(x: str) -> Optional[bool]:
    if x is None:
        return None
    s = x.strip().strip('"').strip("'")
    if not s:
        return None
    sl = s.lower()
    if sl in ("1", "true", "t", "yes", "y", "on"):
        return True
    if sl in ("0", "false", "f", "no", "n", "off"):
        return False
    try:
        v = float(s)
        if math.isnan(v):
            return None
        return v > 0.0
    except Exception:
        return None


def _infer_delimiter(sample: str) -> str:
    if "," in sample:
        return ","
    if "\t" in sample:
        return "\t"
    if ";" in sample:
        return ";"
    return " "


def _load_trace_file(path: str, max_len: int) -> List[bool]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with _open_text_maybe_gzip(path) as f:
            data = json.load(f)
        out: List[bool] = []
        if isinstance(data, dict):
            for key in ("has_spot", "availability", "available", "spot", "values", "trace"):
                if key in data:
                    data = data[key]
                    break
        if isinstance(data, list):
            if len(data) == 0:
                return [False] * max_len
            if isinstance(data[0], dict):
                k = None
                for cand in ("has_spot", "availability", "available", "spot"):
                    if cand in data[0]:
                        k = cand
                        break
                if k is None:
                    k = next(iter(data[0].keys()))
                for row in data:
                    if len(out) >= max_len:
                        break
                    out.append(bool(row.get(k, False)))
            else:
                for v in data:
                    if len(out) >= max_len:
                        break
                    b = _to_bool_token(str(v))
                    out.append(bool(b) if b is not None else False)
        else:
            s = str(data)
            m = re.findall(r"\b[01]\b", s)
            for tok in m[:max_len]:
                out.append(tok == "1")
        if len(out) < max_len:
            out.extend([False] * (max_len - len(out)))
        return out[:max_len]

    # Text/CSV-like
    with _open_text_maybe_gzip(path) as f:
        sample = f.read(8192)
        if not sample:
            return [False] * max_len
        f.seek(0)

        delim = _infer_delimiter(sample)
        # Determine if header present
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        has_header = any(c.isalpha() for c in first_line)

        if delim == " ":
            # whitespace separated
            # Try detect header-like first line
            lines = []
            for _ in range(256):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    lines.append(line)
            # Infer column count and pick best 0/1-like column
            rows = [ln.split() for ln in lines]
            col_idx = 0
            if rows:
                ncol = max(len(r) for r in rows)
                best_score = -1
                best_idx = 0
                start = 1 if has_header else 0
                for j in range(ncol):
                    score = 0
                    total = 0
                    for r in rows[start:]:
                        if j >= len(r):
                            continue
                        total += 1
                        tok = r[j]
                        if tok in ("0", "1"):
                            score += 1
                        else:
                            b = _to_bool_token(tok)
                            if b is not None and (tok.strip() in ("0", "1", "0.0", "1.0") or abs(float(tok)) <= 1.0):
                                score += 1
                    if total > 0 and score > best_score:
                        best_score = score
                        best_idx = j
                col_idx = best_idx

            # Now parse full file
            f.seek(0)
            out: List[bool] = []
            first = True
            for line in f:
                if len(out) >= max_len:
                    break
                line = line.strip()
                if not line:
                    continue
                if first and has_header:
                    first = False
                    continue
                first = False
                parts = line.split()
                if col_idx >= len(parts):
                    continue
                b = _to_bool_token(parts[col_idx])
                out.append(bool(b) if b is not None else False)
            if len(out) < max_len:
                out.extend([False] * (max_len - len(out)))
            return out[:max_len]

        # Delimited (CSV/TSV/;)
        reader = csv.reader(f, delimiter=delim)
        header = None
        first_row = None
        try:
            first_row = next(reader)
        except StopIteration:
            return [False] * max_len

        if has_header:
            header = [h.strip().lower() for h in first_row]
        else:
            # treat as data; reset by starting with first_row included
            pass

        col_idx = None
        if header is not None:
            preferred = ("has_spot", "availability", "available", "spot", "is_available", "avail", "interrupt", "preempt")
            for i, h in enumerate(header):
                for p in preferred:
                    if p in h:
                        col_idx = i
                        break
                if col_idx is not None:
                    break

        # If no header-based column chosen, infer column index by looking for 0/1 patterns
        if col_idx is None:
            # sample some rows (including first_row if it's data)
            rows = []
            if header is None:
                rows.append(first_row)
            for _ in range(256):
                try:
                    r = next(reader)
                except StopIteration:
                    break
                rows.append(r)
            if not rows:
                return [False] * max_len
            ncol = max(len(r) for r in rows)
            best_score = -1.0
            best_idx = 0
            for j in range(ncol):
                score = 0
                total = 0
                for r in rows:
                    if j >= len(r):
                        continue
                    total += 1
                    tok = r[j].strip()
                    if tok in ("0", "1"):
                        score += 1
                    else:
                        b = _to_bool_token(tok)
                        if b is not None:
                            try:
                                v = float(tok)
                                if v in (0.0, 1.0) or (-1.0 <= v <= 1.0):
                                    score += 0.5
                            except Exception:
                                score += 0.25
                if total > 0:
                    norm = score / total
                    if norm > best_score:
                        best_score = norm
                        best_idx = j
            col_idx = best_idx

            # Rewind and re-read with determined delimiter to parse all rows
            f.seek(0)
            reader = csv.reader(f, delimiter=delim)
            out: List[bool] = []
            for row in reader:
                if len(out) >= max_len:
                    break
                if not row:
                    continue
                tok = row[col_idx].strip() if col_idx < len(row) else ""
                b = _to_bool_token(tok)
                if b is None:
                    continue
                out.append(bool(b))
            if len(out) < max_len:
                out.extend([False] * (max_len - len(out)))
            return out[:max_len]

        # Header exists and col_idx chosen; parse remaining rows
        out: List[bool] = []
        for row in reader:
            if len(out) >= max_len:
                break
            if not row or col_idx >= len(row):
                continue
            b = _to_bool_token(row[col_idx])
            out.append(bool(b) if b is not None else False)
        if len(out) < max_len:
            out.extend([False] * (max_len - len(out)))
        return out[:max_len]


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    SPOT_PRICE_PER_HR = 0.9701
    ON_DEMAND_PRICE_PER_HR = 3.06

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "rt", encoding="utf-8") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        self._deadline = float(getattr(self, "deadline", float(config["deadline"]) * 3600.0))
        td = getattr(self, "task_duration", None)
        if isinstance(td, list):
            td = float(td[0]) if td else float(config["duration"]) * 3600.0
        self._task_duration = float(td) if td is not None else float(config["duration"]) * 3600.0
        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, list):
            ro = float(ro[0]) if ro else float(config["overhead"]) * 3600.0
        self._restart_overhead = float(ro) if ro is not None else float(config["overhead"]) * 3600.0

        self._done_total = 0.0
        self._done_len = 0

        self._od_lock = False

        self._has_traces = False
        self._spot: List[bytearray] = []
        self._run_len: List[array] = []
        self._next_on: List[array] = []
        self._sentinel = 0
        self._steps = 0

        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        trace_files = config.get("trace_files", None)
        if isinstance(trace_files, list) and trace_files:
            # Determine how many steps we need.
            steps_needed = int(math.ceil(self._deadline / self._gap)) + 3
            self._steps = steps_needed
            self._sentinel = steps_needed + 5

            num_regions = None
            try:
                num_regions = int(self.env.get_num_regions())
            except Exception:
                num_regions = len(trace_files)
            num_regions = max(1, min(num_regions, len(trace_files)))

            spot_list: List[bytearray] = []
            run_list: List[array] = []
            next_list: List[array] = []

            for i in range(num_regions):
                tf = trace_files[i]
                if not os.path.isabs(tf):
                    tf = os.path.join(spec_dir, tf)
                try:
                    avail = _load_trace_file(tf, steps_needed)
                except Exception:
                    avail = [False] * steps_needed
                b = bytearray(1 if x else 0 for x in avail[:steps_needed])
                if len(b) < steps_needed:
                    b.extend(b"\x00" * (steps_needed - len(b)))

                rl = array("I", [0]) * steps_needed
                no = array("I", [0]) * steps_needed
                next_val = self._sentinel
                run_val = 0
                for t in range(steps_needed - 1, -1, -1):
                    if b[t]:
                        run_val += 1
                        next_val = t
                    else:
                        run_val = 0
                    rl[t] = run_val
                    no[t] = next_val

                spot_list.append(b)
                run_list.append(rl)
                next_list.append(no)

            self._spot = spot_list
            self._run_len = run_list
            self._next_on = next_list
            self._has_traces = True

        # Minimum spot run length (when starting spot fresh) to be cost-effective vs on-demand.
        ratio = self.SPOT_PRICE_PER_HR / self.ON_DEMAND_PRICE_PER_HR
        denom = max(1e-9, (1.0 - ratio))
        min_steps = int(math.ceil((self._restart_overhead / (self._gap * denom)) - 1e-12))
        if min_steps < 1:
            min_steps = 1
        # Also require at least enough steps to get positive work
        min_pos = int(math.floor(self._restart_overhead / self._gap)) + 1
        if min_steps < min_pos:
            min_steps = min_pos
        self._min_spot_start_steps = min_steps

        # Lock-on-demand threshold: when slack gets too low, avoid restarts.
        self._od_lock_slack = max(3.0 * self._gap, 2.0 * self._restart_overhead)

        return self

    def _sync_done_total(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n > self._done_len:
            self._done_total += sum(td[self._done_len : n])
            self._done_len = n

    def _t_idx(self) -> int:
        e = float(getattr(self.env, "elapsed_seconds", 0.0))
        if self._gap <= 0:
            return 0
        t = int(e // self._gap)
        if t < 0:
            return 0
        if self._steps > 0 and t >= self._steps:
            return self._steps - 1
        return t

    def _maybe_switch_best_region(self, t_idx: int) -> None:
        if not self._has_traces:
            return
        try:
            cur = int(self.env.get_current_region())
            nreg = int(self.env.get_num_regions())
        except Exception:
            return
        if nreg <= 1:
            return
        look_t = t_idx + 1
        if look_t < 0:
            look_t = 0
        if look_t >= self._steps:
            look_t = self._steps - 1

        best_r = cur
        best_next = self._sentinel
        best_run = 0

        for r in range(min(nreg, len(self._next_on))):
            t_on = self._next_on[r][look_t]
            if t_on >= self._sentinel:
                continue
            run = self._run_len[r][t_on]
            if t_on < best_next or (t_on == best_next and run > best_run):
                best_next = t_on
                best_run = run
                best_r = r

        if best_next < self._sentinel and best_r != cur:
            try:
                self.env.switch_region(best_r)
            except Exception:
                pass

    def _current_run_len(self, t_idx: int) -> int:
        if not self._has_traces:
            return 1
        try:
            r = int(self.env.get_current_region())
        except Exception:
            return 1
        if r < 0 or r >= len(self._run_len):
            return 1
        if t_idx < 0:
            t_idx = 0
        if t_idx >= self._steps:
            t_idx = self._steps - 1
        return int(self._run_len[r][t_idx])

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._sync_done_total()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = self._deadline - elapsed
        remaining_work = self._task_duration - self._done_total

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if remaining_time <= 1e-9:
            return ClusterType.ON_DEMAND

        t_idx = self._t_idx()

        # Remaining slack after accounting for the one-time restart overhead needed to (re)start guaranteed execution.
        slack_for_restart = remaining_time - remaining_work - self._restart_overhead

        if (not self._od_lock) and slack_for_restart <= self._od_lock_slack:
            self._od_lock = True

        if self._od_lock:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Feasibility check: can we idle for one step and still finish by switching to on-demand afterwards?
        can_idle = remaining_work <= (remaining_time - self._gap - self._restart_overhead + 1e-9)

        if not can_idle:
            # Must make progress now.
            if has_spot:
                if last_cluster_type == ClusterType.SPOT:
                    return ClusterType.SPOT
                run_len = self._current_run_len(t_idx)
                if run_len >= self._min_spot_start_steps:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Not urgent: prefer cheap progress on spot when it is worthwhile, else idle and reposition.
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switch back only if it's clearly worthwhile.
                run_len = self._current_run_len(t_idx)
                if run_len >= self._min_spot_start_steps:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            # last is NONE or other: start spot only if run window amortizes overhead reasonably.
            run_len = self._current_run_len(t_idx)
            if run_len >= self._min_spot_start_steps:
                return ClusterType.SPOT
            self._maybe_switch_best_region(t_idx)
            return ClusterType.NONE

        # No spot: idle and reposition.
        self._maybe_switch_best_region(t_idx)
        return ClusterType.NONE