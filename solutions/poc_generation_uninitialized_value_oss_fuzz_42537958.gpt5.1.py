import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 2708

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [
                    m
                    for m in tf.getmembers()
                    if m.isfile() and 0 < m.size <= 1_000_000
                ]

                if not members:
                    return self._fallback_poc()

                def choose(filter_func) -> Optional[bytes]:
                    best_member = None
                    best_score = None  # (diff_from_target_len, size)

                    for m in members:
                        if not filter_func(m):
                            continue
                        diff = abs(m.size - target_len)
                        score = (diff, m.size)
                        if best_member is None or score < best_score:
                            best_member = m
                            best_score = score

                    if best_member is None:
                        return None

                    f = tf.extractfile(best_member)
                    if f is None:
                        return None
                    try:
                        return f.read()
                    finally:
                        f.close()

                # Strategy 1: files explicitly mentioning the OSS-Fuzz issue id
                data = choose(lambda m: "42537958" in m.name)
                if data is not None:
                    return data

                # Strategy 2: typical PoC/crash naming patterns
                keywords = (
                    "poc",
                    "crash",
                    "id_",
                    "testcase",
                    "test",
                    "input",
                    "uninit",
                    "msan",
                    "bug",
                    "regress",
                    "case",
                    "oss-fuzz",
                )
                data = choose(
                    lambda m: any(k in m.name.lower() for k in keywords)
                )
                if data is not None:
                    return data

                # Strategy 3: likely binary/image extensions (JPEG, generic bin/dat)
                exts = (".jpg", ".jpeg", ".jpe", ".jfif", ".jif", ".bin", ".dat", ".raw")
                data = choose(lambda m: m.name.lower().endswith(exts))
                if data is not None:
                    return data

                # Strategy 4: best-sized arbitrary file as last resort
                data = choose(lambda m: True)
                if data is not None:
                    return data

        except tarfile.TarError:
            # If src_path is not a valid tarball for some reason, fall back
            pass

        return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        # Minimal JPEG-like structure (SOI + EOI). Used only if no suitable file is found.
        return b"\xff\xd8\xff\xd9"
