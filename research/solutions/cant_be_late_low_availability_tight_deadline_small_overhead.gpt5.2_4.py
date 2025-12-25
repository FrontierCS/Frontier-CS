import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._args = args

        self._initialized = False
        self._last_elapsed = -1.0

        self._od_committed = False
        self._outage_seconds = 0.0
        self._od_start_elapsed = None  # type: Optional[float]
        self._last_choice = ClusterType.NONE

        self._spot_streak = 0
        self._buffer_seconds = 0.0
        self._outage_wait_cap_seconds = 0.0
        self._od_min_run_seconds = 0.0
        self._spot_slack_required_seconds = 0.0
        self._od_to_spot_min_streak = 1

    def solve(self, spec_path: str) -> "Solution":
        # Keep stateless w.r.t. spec; evaluator may reuse instance across episodes.
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _compute_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0

        if isinstance(t, (int, float)):
            return max(0.0, float(t))

        if isinstance(t, (list, tuple)):
            if not t:
                return 0.0

            # All numeric?
            all_numeric = True
            nums = []
            for item in t:
                if isinstance(item, (int, float)):
                    nums.append(float(item))
                else:
                    all_numeric = False
                    break

            if all_numeric:
                # If nondecreasing, treat as cumulative "done time" and use last.
                nondecreasing = True
                for i in range(1, len(nums)):
                    if nums[i] < nums[i - 1] - 1e-9:
                        nondecreasing = False
                        break
                if nondecreasing:
                    return max(0.0, nums[-1])
                return max(0.0, sum(nums))

            total = 0.0
            count_any = 0
            for item in t:
                if isinstance(item, (int, float)):
                    total += float(item)
                    count_any += 1
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    a, b = item[0], item[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        total += float(b) - float(a)
                        count_any += 1
                elif isinstance(item, dict):
                    if "duration" in item and isinstance(item["duration"], (int, float)):
                        total += float(item["duration"])
                        count_any += 1
                    elif (
                        "start" in item
                        and "end" in item
                        and isinstance(item["start"], (int, float))
                        and isinstance(item["end"], (int, float))
                    ):
                        total += float(item["end"]) - float(item["start"])
                        count_any += 1

            if count_any > 0:
                return max(0.0, total)

            # Fallback: if last element is numeric, treat as cumulative.
            last = t[-1]
            if isinstance(last, (int, float)):
                return max(0.0, float(last))

        return 0.0

    def _reset_episode_state(self) -> None:
        self._od_committed = False
        self._outage_seconds = 0.0
        self._od_start_elapsed = None
        self._last_choice = ClusterType.NONE
        self._spot_streak = 0

    def _lazy_init(self) -> None:
        if self._initialized:
            return

        gap = self._safe_float(getattr(self.env, "gap_seconds", 60.0), 60.0)
        restart = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        task_dur = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)

        slack_total = max(0.0, deadline - task_dur)

        # Conservative, but not overly: buffer scales with available slack and restart.
        self._buffer_seconds = max(
            900.0,  # 15 minutes
            12.0 * restart,
            10.0 * gap,
            0.15 * slack_total,
        )

        # Max time to "wait for spot" during an outage before switching to on-demand.
        self._outage_wait_cap_seconds = max(0.0, min(3.0 * 3600.0, 0.5 * slack_total))

        # Once we start OD (not committed), keep it for a minimum time to avoid thrashing.
        self._od_min_run_seconds = max(1800.0, 10.0 * gap)

        # Only switch from OD->SPOT if slack is comfortably above buffer.
        self._spot_slack_required_seconds = self._buffer_seconds + max(1800.0, 0.10 * slack_total)

        # Only switch from OD->SPOT if spot has been available for a few consecutive steps.
        # This reduces OD<->SPOT thrashing with tiny spot windows.
        if gap > 0 and restart > 0:
            self._od_to_spot_min_streak = max(1, int(math.ceil(restart / gap)))
        else:
            self._od_to_spot_min_streak = 1

        self._initialized = True

    def _enter_od(self) -> ClusterType:
        if self._od_start_elapsed is None:
            self._od_start_elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        self._last_choice = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND

    def _enter_none(self) -> ClusterType:
        self._od_start_elapsed = None
        self._last_choice = ClusterType.NONE
        return ClusterType.NONE

    def _enter_spot(self) -> ClusterType:
        self._od_start_elapsed = None
        self._last_choice = ClusterType.SPOT
        return ClusterType.SPOT

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        if self._last_elapsed >= 0.0 and elapsed + 1e-9 < self._last_elapsed:
            # New episode detected.
            self._reset_episode_state()
        self._last_elapsed = elapsed

        gap = self._safe_float(getattr(self.env, "gap_seconds", 60.0), 60.0)

        # Track spot-availability streak (independent of what we choose).
        if has_spot:
            self._spot_streak += 1
        else:
            self._spot_streak = 0

        done = self._compute_done_seconds()
        task_dur = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)

        work_remaining = max(0.0, task_dur - done)
        if work_remaining <= 1e-9:
            self._od_committed = False
            self._outage_seconds = 0.0
            return self._enter_none()

        time_remaining = max(0.0, deadline - elapsed)
        slack = time_remaining - work_remaining

        # If already impossible or extremely tight, always OD (maximize chance).
        if slack <= self._buffer_seconds:
            self._od_committed = True
            self._outage_seconds = 0.0
            return self._enter_od()

        if self._od_committed:
            self._outage_seconds = 0.0
            return self._enter_od()

        # Not committed: use spot aggressively when it's available, but avoid thrashing from OD->SPOT.
        if has_spot:
            self._outage_seconds = 0.0

            if self._last_choice == ClusterType.ON_DEMAND and self._od_start_elapsed is not None:
                od_run = elapsed - self._od_start_elapsed
                # Keep OD for minimum runtime, or if slack is not comfortably large.
                if od_run + 1e-9 < self._od_min_run_seconds:
                    return self._enter_od()
                if slack < self._spot_slack_required_seconds:
                    return self._enter_od()
                # Require some stability in spot availability before switching from OD.
                if self._spot_streak < self._od_to_spot_min_streak:
                    return self._enter_od()

            return self._enter_spot()

        # No spot available: decide between waiting (NONE) and OD.
        self._outage_seconds += max(0.0, gap)

        remaining_wait_budget = max(0.0, slack - self._buffer_seconds)
        wait_limit = min(self._outage_wait_cap_seconds, remaining_wait_budget)

        # If we can't afford to wait, or we've waited long enough, go OD.
        if remaining_wait_budget <= 1e-9 or self._outage_seconds + 1e-9 >= wait_limit:
            return self._enter_od()

        # Otherwise wait for spot to return.
        return self._enter_none()

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)