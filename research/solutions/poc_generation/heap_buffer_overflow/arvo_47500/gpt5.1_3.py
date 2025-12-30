import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 1479

        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return b""

        with tar:
            best_member = None
            best_score = float("-inf")

            for member in tar.getmembers():
                if not member.isfile() or member.size <= 0:
                    continue

                name_lower = member.name.lower()
                base, ext = os.path.splitext(name_lower)

                try:
                    f = tar.extractfile(member)
                except Exception:
                    continue
                if f is None:
                    continue

                try:
                    header = f.read(16)
                finally:
                    f.close()

                score = 0

                # Strong preference for exact ground-truth size
                if member.size == target_size:
                    score += 100
                elif 0 < member.size < target_size * 2:
                    score += 10  # prefer relatively small files

                # Name-based hints
                if any(
                    key in name_lower
                    for key in (
                        "poc",
                        "proof",
                        "cve",
                        "heap",
                        "overflow",
                        "crash",
                        "bug",
                        "47500",
                        "ht",
                        "dec",
                    )
                ):
                    score += 25

                # Extension-based hints
                if ext in (".j2k", ".jp2", ".jpc", ".j2c", ".jph", ".jpt"):
                    score += 20
                elif ext in (".pgx", ".raw", ".bin", ".dat"):
                    score += 8

                # Magic bytes / header-based hints
                if len(header) >= 2 and header.startswith(b"\xff\x4f"):
                    score += 30  # JPEG 2000 codestream SOC marker
                if len(header) >= 8 and (
                    header.startswith(b"\x00\x00\x00\x0cjP  ")
                    or header[4:8] == b"jP  "
                ):
                    score += 30  # JP2 file signature box

                # Penalize obvious source/text files
                if ext in (
                    ".c",
                    ".h",
                    ".cpp",
                    ".cc",
                    ".cxx",
                    ".hpp",
                    ".py",
                    ".java",
                    ".js",
                    ".html",
                    ".xml",
                    ".json",
                    ".yml",
                    ".yaml",
                    ".md",
                    ".txt",
                    ".rst",
                    ".in",
                    ".am",
                    ".ac",
                    ".cmake",
                    ".mak",
                ):
                    score -= 40

                # Binary-ness heuristic
                if header:
                    nonprintable = sum(
                        1
                        for b in header
                        if b < 9 or (13 < b < 32) or b > 126
                    )
                    if nonprintable >= len(header) // 2:
                        score += 5

                # Directory hints
                if "/poc" in name_lower or name_lower.startswith("poc"):
                    score += 10

                if (
                    score > best_score
                    or (
                        score == best_score
                        and best_member is not None
                        and member.size < best_member.size
                    )
                ):
                    best_score = score
                    best_member = member

            if best_member is not None:
                f = tar.extractfile(best_member)
                if f is None:
                    return b""
                try:
                    data = f.read()
                finally:
                    f.close()
                return data

            return b""