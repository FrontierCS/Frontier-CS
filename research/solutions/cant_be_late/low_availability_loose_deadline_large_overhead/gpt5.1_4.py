from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        # Whether we've committed to always using on-demand from now on.
        self.in_fallback_od = False
        # Number of times we observed a spot preemption while we were using spot.
        self.spot_failures = 0

        # Hyperparameters with safe defaults; can be overridden via CLI args if desired.
        # Max number of spot preemptions tolerated before permanently switching to on-demand.
        default_max_failures = 4
        if args is not None and hasattr(args, "max_spot_failures"):
            try:
                self.max_spot_failures = int(args.max_spot_failures)
            except Exception:
                self.max_spot_failures = default_max_failures
        else:
            self.max_spot_failures = default_max_failures
        if self.max_spot_failures < 1:
            self.max_spot_failures = 1

        # Safety buffer (in hours) added on top of estimated remaining work when deciding to switch to OD.
        default_buffer_hours = 2.0
        if args is not None and hasattr(args, "safety_buffer_hours"):
            try:
                self.safety_buffer_hours = float(args.safety_buffer_hours)
            except Exception:
                self.safety_buffer_hours = default_buffer_hours
        else:
            self.safety_buffer_hours = default_buffer_hours
        if self.safety_buffer_hours < 0.0:
            self.safety_buffer_hours = 0.0
        self.safety_buffer_seconds = self.safety_buffer_hours * 3600.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: load configuration from spec_path if needed.
        return self

    def _estimate_remaining_work(self) -> float:
        """Estimate remaining base task work (in seconds) using task_done_time."""
        task_duration = getattr(self, "task_duration", None)
        if task_duration is None:
            return 0.0
        try:
            total = float(task_duration)
        except Exception:
            return 0.0

        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return total

        # Attempt to infer representation of task_done_time
        try:
            first = tdt[0]
        except Exception:
            return total

        done = 0.0
        # Case 1: list of segments (start, end)
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            segs = []
            for seg in tdt:
                try:
                    s, e = seg[0], seg[1]
                    s = float(s)
                    e = float(e)
                    if e > s:
                        segs.append((s, e))
                except Exception:
                    continue
            if not segs:
                done = 0.0
            else:
                # Merge intervals to avoid double-counting overlapping work.
                segs.sort(key=lambda x: x[0])
                cur_s, cur_e = segs[0]
                for s, e in segs[1:]:
                    if s <= cur_e:
                        if e > cur_e:
                            cur_e = e
                    else:
                        done += cur_e - cur_s
                        cur_s, cur_e = s, e
                done += cur_e - cur_s
        else:
            # Case 2: numeric list; treat as durations or cumulative progress.
            all_numeric = True
            done = 0.0
            for x in tdt:
                try:
                    done += float(x)
                except Exception:
                    all_numeric = False
                    break
            if not all_numeric:
                # Fallback: last element as cumulative done time.
                try:
                    done = float(tdt[-1])
                except Exception:
                    done = 0.0

        if done < 0.0:
            done = 0.0
        if done > total:
            done = total
        remaining = total - done
        return remaining

    def _should_switch_to_od(self) -> bool:
        """Decide if we should permanently switch to on-demand based on time and progress."""
        if self.in_fallback_od:
            return True

        try:
            elapsed = float(self.env.elapsed_seconds)
            deadline = float(self.deadline)
        except Exception:
            return False

        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Past deadline or exactly at it: OD is the only sensible choice.
            return True

        remaining = self._estimate_remaining_work()
        # Required time if we switch now: remaining work + safety buffer
        required_time = remaining + self.safety_buffer_seconds

        # If the remaining wall-clock time is less than or equal to what we'd need on OD
        # (plus buffer), switch to OD.
        if time_left <= required_time:
            return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track spot preemptions: last step we were on SPOT, now spot is unavailable.
        if (
            last_cluster_type == ClusterType.SPOT
            and not has_spot
            and not self.in_fallback_od
        ):
            self.spot_failures += 1
            if self.spot_failures >= self.max_spot_failures:
                self.in_fallback_od = True

        # Time- and progress-based decision to switch to on-demand permanently.
        if not self.in_fallback_od and self._should_switch_to_od():
            self.in_fallback_od = True

        # Phase 2: once in fallback mode, always choose on-demand.
        if self.in_fallback_od:
            return ClusterType.ON_DEMAND

        # Phase 1: Prefer spot whenever available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and still in phase 1: wait (no cost) and consume slack.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)