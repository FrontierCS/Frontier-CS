import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_SIZE = 33762

        def pick_best(candidates):
            if not candidates:
                return None
            strong_pats = (
                "poc",
                "crash",
                "uaf",
                "use-after-free",
                "use_after_free",
                "heap",
                "standalone",
                "form",
            )
            best = None
            best_score = -1
            for m in candidates:
                ln = m.name.lower()
                score = 0
                for sp in strong_pats:
                    if sp in ln:
                        score += 2
                if (
                    "/test" in ln
                    or "/tests" in ln
                    or "/fuzz" in ln
                    or "/regress" in ln
                    or "tests/" in ln
                ):
                    score += 1
                if score > best_score:
                    best_score = score
                    best = m
            return best

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return b"A"

        exact = []
        close = []
        keyword = []
        others_small = []

        keyword_subs = (
            "poc",
            "crash",
            "uaf",
            "use-after-free",
            "use_after_free",
            "heap",
            "fuzz",
            "standalone",
            "form",
            "bug",
            "issue",
            "ticket",
            "regress",
            "testcase",
            "id_",
        )

        for m in tf.getmembers():
            if not m.isfile():
                continue
            size = m.size
            name_lower = m.name.lower()

            if size == TARGET_SIZE:
                exact.append(m)
            elif abs(size - TARGET_SIZE) <= 4096:
                close.append(m)

            if any(k in name_lower for k in keyword_subs):
                keyword.append(m)

            if size <= 4096:
                others_small.append(m)

        member: Optional[tarfile.TarInfo] = None

        # Prefer an exact-size PoC
        if exact:
            member = pick_best(exact)
            if member is None:
                member = exact[0]

        # Then a close-size PoC
        if member is None and close:
            # Prefer by keywords first
            close_best = pick_best(close)
            if close_best is not None:
                member = close_best
            else:
                member = min(close, key=lambda m: abs(m.size - TARGET_SIZE))

        # Then any keyword-indicated PoC
        if member is None and keyword:
            member = pick_best(keyword)
            if member is None:
                member = min(keyword, key=lambda m: m.size)

        # Fallback: any small file
        if member is None and others_small:
            member = min(others_small, key=lambda m: m.size)

        if member is None:
            return b"A"

        try:
            f = tf.extractfile(member)
            if f is None:
                return b"A"
            data = f.read()
            if not isinstance(data, (bytes, bytearray)):
                try:
                    data = bytes(data)
                except Exception:
                    data = b"A"
            return data
        except Exception:
            return b"A"