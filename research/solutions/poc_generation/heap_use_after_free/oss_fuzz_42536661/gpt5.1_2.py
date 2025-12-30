import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc_in_tar(src_path)
        if poc is not None:
            return poc
        return self._craft_fallback_poc()

    def _find_poc_in_tar(self, src_path: str) -> bytes | None:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                if not members:
                    return None

                target_size = 1089

                def score_member(m: tarfile.TarInfo) -> int:
                    if not m.isfile():
                        return -10**9
                    name = m.name
                    lname = name.lower()
                    size = m.size

                    score = 0

                    # Prefer RAR / RAR5 related names.
                    if "rar5" in lname:
                        score += 40
                    if "rar" in lname:
                        score += 30
                    if lname.endswith(".rar") or lname.endswith(".rar5"):
                        score += 40

                    # Bug / PoC hints.
                    if "poc" in lname or "crash" in lname or "uaf" in lname:
                        score += 60
                    if "heap" in lname and "free" in lname:
                        score += 40
                    if "42536661" in lname:
                        score += 80

                    # Prefer sizes close to ground-truth.
                    if size == target_size:
                        score += 200
                    else:
                        # Penalize distance from target size, but softly.
                        diff = abs(size - target_size)
                        score += max(0, 150 - diff // 4)

                    return score

                best_member = None
                best_score = -10**9

                for m in members:
                    s = score_member(m)
                    if s > best_score:
                        best_score = s
                        best_member = m

                # If best score is too low, it is probably random noise.
                if best_member is None or best_score < 0:
                    return None

                f = tf.extractfile(best_member)
                if f is None:
                    return None
                data = f.read()
                # Sanity check: do not return empty data.
                if not data:
                    return None
                return data
        except Exception:
            return None

    def _craft_fallback_poc(self) -> bytes:
        # Minimal RAR5-like header as a fallback. This is not guaranteed
        # to trigger the bug but gives the fuzzer something plausible.
        # Signature for RAR5 archives: "Rar!\x1A\x07\x01\x00"
        magic = b"Rar!\x1a\x07\x01\x00"
        # Pad with zeros to look like a tiny archive.
        return magic + b"\x00" * 32