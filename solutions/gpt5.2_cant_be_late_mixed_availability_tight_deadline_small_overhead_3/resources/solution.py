import argparse
import json
import os
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._cfg = {
            "min_buffer_seconds": 600.0,
        }
        self._reset_runtime_state()

    def _reset_runtime_state(self):
        self._initialized = False
        self._committed_od = False
        self._steps = 0
        self._spot_available_steps = 0
        self._interruptions = 0
        self._spot_available_streak = 0
        self._spot_unavailable_streak = 0
        self._last_elapsed = None
        self._last_done = None
        self._min_start_streak = 1

    def solve(self, spec_path: str) -> "Solution":
        # Optional: read JSON config if provided.
        try:
            if spec_path and os.path.isfile(spec_path):
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read().strip()
                if txt:
                    try:
                        cfg = json.loads(txt)
                        if isinstance(cfg, dict):
                            mb = cfg.get("min_buffer_seconds", None)
                            if isinstance(mb, (int, float)) and mb > 0:
                                self._cfg["min_buffer_seconds"] = float(mb)
                    except Exception:
                        pass
        except Exception:
            pass
        self._reset_runtime_state()
        return self

    @staticmethod
    def _is_non_decreasing(seq) -> bool:
        try:
            prev = None
            for x in seq:
                xv = float(x)
                if prev is not None and xv < prev - 1e-12:
                    return False
                prev = xv
            return True
        except Exception:
            return False

    def _get_done_work_seconds(self) -> float:
        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        # Case: list of segments (start, end)
        try:
            first = tdt[0]
            if isinstance(first, (tuple, list)) and len(first) == 2:
                s = 0.0
                for seg in tdt:
                    if isinstance(seg, (tuple, list)) and len(seg) == 2:
                        a = float(seg[0])
                        b = float(seg[1])
                        if b > a:
                            s += (b - a)
                if s < 0:
                    s = 0.0
                return min(td, s)
        except Exception:
            pass

        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)

        # Case: numeric list
        s = None
        try:
            s = float(sum(float(x) for x in tdt))
        except Exception:
            s = None

        c = None
        if gap > 0:
            try:
                c = float(len(tdt)) * gap
            except Exception:
                c = None

        candidates = []
        for v in (s, c):
            if isinstance(v, (int, float)) and v >= 0.0 and v <= td * 1.2:
                candidates.append(float(v))

        # Case: cumulative done-work series
        try:
            last = float(tdt[-1])
            if last >= 0.0 and last <= td * 1.2 and self._is_non_decreasing(tdt):
                candidates.append(last)
        except Exception:
            pass

        if candidates:
            return min(td, max(candidates))

        # Fallback
        best = 0.0
        for v in (s, c):
            if isinstance(v, (int, float)) and v > best:
                best = float(v)
        if best < 0.0:
            best = 0.0
        return min(td, best)

    def _critical_buffer_seconds(self) -> float:
        env = getattr(self, "env", None)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        base = max(
            float(self._cfg.get("min_buffer_seconds", 600.0)),
            3.0 * ro,
            3.0 * gap,
        )

        # Add a little extra to account for step discretization and any immediate transition.
        base += 2.0 * gap

        # Never exceed total slack (if known) by too much; but keep at least base.
        try:
            slack_total = float(getattr(self, "deadline", 0.0) or 0.0) - float(getattr(self, "task_duration", 0.0) or 0.0)
            if slack_total > 0:
                base = min(base, max(0.75 * slack_total, base))
        except Exception:
            pass

        return float(base)

    def _maybe_init(self):
        if self._initialized:
            return
        env = getattr(self, "env", None)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if gap > 0 and ro / gap > 0.55:
            self._min_start_streak = 2
        else:
            self._min_start_streak = 1
        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init()

        env = self.env
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_work_seconds()
        if self._last_elapsed is not None:
            # Detect new episode/reset.
            if elapsed + 1e-9 < float(self._last_elapsed):
                self._reset_runtime_state()
                self._maybe_init()
                elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
                done = self._get_done_work_seconds()
            else:
                # Also reset if done decreases significantly.
                if self._last_done is not None and done + 1e-6 < float(self._last_done):
                    self._reset_runtime_state()
                    self._maybe_init()
                    elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
                    done = self._get_done_work_seconds()

        self._last_elapsed = elapsed
        self._last_done = done

        td = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, td - done)

        # If finished (or extremely close), stop spending.
        if remaining_work <= max(1e-6, 0.1 * gap):
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)
        slack_remaining = remaining_time - remaining_work

        self._steps += 1
        if has_spot:
            self._spot_available_steps += 1
            self._spot_available_streak += 1
            self._spot_unavailable_streak = 0
        else:
            self._spot_unavailable_streak += 1
            self._spot_available_streak = 0

        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._interruptions += 1

        buffer = self._critical_buffer_seconds()

        # Hard feasibility guard: if we cannot afford any more non-progress time, commit to on-demand.
        # Include a bit for (re)start overhead and discretization.
        if slack_remaining <= buffer or remaining_time <= remaining_work + ro + 2.0 * gap:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            # If we're already on spot, keep running.
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            # Optional: avoid starting on the very first step of a new availability burst when overhead is large,
            # unless slack is tight enough that we must take any opportunity.
            if self._min_start_streak > 1 and self._spot_available_streak < self._min_start_streak and slack_remaining > 2.0 * buffer:
                return ClusterType.NONE

            return ClusterType.SPOT

        # No spot: wait for spot while slack permits.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        if parser is None:
            parser = argparse.ArgumentParser(add_help=False)
        args, _ = parser.parse_known_args()
        return cls(args)
