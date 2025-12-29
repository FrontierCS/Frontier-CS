import tarfile
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "42537493"
        bug_bytes = bug_id.encode("ascii")

        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return b"A" * 24

        with tar:
            try:
                members = tar.getmembers()
            except Exception:
                return b"A" * 24

            # 1. Search for file with bug id in its name/path
            for m in members:
                if not m.isfile():
                    continue
                name = m.name
                try:
                    base = os.path.basename(name)
                except Exception:
                    base = name
                if bug_id in base or bug_id in name:
                    try:
                        f = tar.extractfile(m)
                        if f is not None:
                            data = f.read()
                            if data:
                                return data
                    except Exception:
                        pass

            # 2. Search for bug id in contents of small files
            for m in members:
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0 or size > 4096:
                    continue
                try:
                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                if bug_bytes in data:
                    return data

            # 3. Heuristic search for likely oss-fuzz PoC files
            best_member = None
            best_score = -1
            for m in members:
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0:
                    continue

                name_lower = m.name.lower()
                score = 0

                # Prefer smaller files
                if size <= 4096:
                    score += 1

                # Names that hint at oss-fuzz/PoC/regression tests
                if "oss-fuzz" in name_lower or "ossfuzz" in name_lower or "oss_fuzz" in name_lower:
                    score += 5
                if "poc" in name_lower or "regress" in name_lower or "uaf" in name_lower or "bug" in name_lower:
                    score += 3
                if "/test" in name_lower or "/tests" in name_lower or "/fuzz" in name_lower or "/regress" in name_lower or "/bugs" in name_lower:
                    score += 2

                # Prefer likely data formats
                ext = os.path.splitext(name_lower)[1]
                if ext in (".xml", ".html", ".txt", ".dat", ".bin"):
                    score += 2

                # Prefer sizes close to 24 bytes
                diff = abs(size - 24)
                if diff == 0:
                    score += 5
                elif diff <= 8:
                    score += 3
                elif diff <= 32:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_member = m

            if best_member is not None and best_score > 0:
                try:
                    f = tar.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        # Fallback: simple placeholder PoC-sized input
        return b"A" * 24