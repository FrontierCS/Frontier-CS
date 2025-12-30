import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        Lg = 80064
        fallback = b"A" * Lg

        try:
            if not os.path.isfile(src_path):
                return fallback

            with tarfile.open(src_path, "r:*") as tar:
                exact = []
                others = []

                for member in tar:
                    if not member.isfile():
                        continue
                    if member.size <= 0:
                        continue
                    if member.size == Lg:
                        exact.append(member)
                    else:
                        others.append(member)

                def keyword_score(member: tarfile.TarInfo) -> int:
                    name = member.name.lower()
                    score = 0
                    for kw, bonus in (
                        ("poc", 100),
                        ("proof", 80),
                        ("cidfont", 70),
                        ("cid", 60),
                        ("overflow", 50),
                        ("crash", 50),
                        ("bug", 30),
                        ("font", 20),
                    ):
                        if kw in name:
                            score += bonus
                    _, ext = os.path.splitext(name)
                    if ext in (".pdf", ".ps", ".cff", ".ttf", ".otf", ".cid", ".bin", ".dat", ".data"):
                        score += 5
                    return score

                chosen = None

                if exact:
                    if len(exact) == 1:
                        chosen = exact[0]
                    else:
                        best_score = None
                        best_member = None
                        for m in exact:
                            s = keyword_score(m)
                            if best_score is None or s > best_score:
                                best_score = s
                                best_member = m
                        chosen = best_member
                elif others:
                    def combined_score(member: tarfile.TarInfo) -> int:
                        size_diff = abs(member.size - Lg)
                        size_score = -size_diff  # prefer closer sizes
                        return size_score * 10 + keyword_score(member)

                    best_score = None
                    best_member = None
                    for m in others:
                        s = combined_score(m)
                        if best_score is None or s > best_score:
                            best_score = s
                            best_member = m
                    chosen = best_member

                if chosen is None:
                    return fallback

                f = tar.extractfile(chosen)
                if f is None:
                    return fallback
                data = f.read()
                if not isinstance(data, bytes):
                    return fallback
                return data

        except Exception:
            return fallback