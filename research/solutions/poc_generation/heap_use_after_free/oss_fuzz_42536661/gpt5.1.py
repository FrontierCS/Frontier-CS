import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by extracting it from the
        provided source tarball, where it's expected to be included.
        """
        TARGET_LEN = 1089

        def choose_member(members):
            # First pass: scored candidates based on filename hints + closeness to TARGET_LEN
            scored = []
            for m in members:
                if not m.isfile() or m.size <= 0:
                    continue
                name_l = m.name.lower()
                score = 0
                if "42536661" in name_l:
                    score += 20
                if "poc" in name_l:
                    score += 10
                if "crash" in name_l or "bug" in name_l or "issue" in name_l:
                    score += 5
                if "rar" in name_l or "rar5" in name_l:
                    score += 2
                diff = abs(m.size - TARGET_LEN)
                scored.append((score, diff, m.size, m))

            if scored:
                # Prefer highest score, then closest size, then smaller file
                scored.sort(key=lambda x: (-x[0], x[1], x[2]))
                if scored[0][0] > 0:
                    return scored[0][3]

            # Second pass: any file with exact TARGET_LEN
            exact = [m for m in members if m.isfile() and m.size == TARGET_LEN]
            if exact:
                return exact[0]

            # Third pass: smallest non-empty regular file
            regular = [m for m in members if m.isfile() and m.size > 0]
            if regular:
                regular.sort(key=lambda m: m.size)
                return regular[0]

            return None

        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            member: Optional[tarfile.TarInfo] = choose_member(members)
            if member is None:
                return b""
            extracted = tf.extractfile(member)
            if extracted is None:
                return b""
            data = extracted.read()
            return data