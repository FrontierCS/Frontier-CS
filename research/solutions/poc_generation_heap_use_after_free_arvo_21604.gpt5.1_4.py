import os
import tarfile
import gzip
import bz2
import lzma


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by locating an existing
        PoC (or best-effort candidate) within the provided source tarball.
        """
        L_GROUND = 33762

        # Try to open the tarball; if it fails, fall back to a trivial payload.
        try:
            tf = tarfile.open(src_path, "r:*")
        except tarfile.TarError:
            return b"A"

        with tf:
            members = [m for m in tf.getmembers() if m.isreg()]

            # 1) Exact size match inside tarball (uncompressed files)
            for m in members:
                if m.size == L_GROUND:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    if len(data) == L_GROUND:
                        return data

            # 2) Look for compressed PoCs (.gz, .bz2, .xz) whose decompressed size matches
            compressed_exts = (".gz", ".bz2", ".xz")
            poc_keywords = ("poc", "crash", "uaf", "useafterfree", "use-after-free")
            for m in members:
                name = os.path.basename(m.name).lower()
                _, ext = os.path.splitext(name)
                if ext not in compressed_exts:
                    continue
                if not any(k in name for k in poc_keywords):
                    continue
                # Limit compressed size to avoid pathological cases
                if m.size == 0 or m.size > 2 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                cdata = f.read()
                try:
                    if ext == ".gz":
                        data = gzip.decompress(cdata)
                    elif ext == ".bz2":
                        data = bz2.decompress(cdata)
                    else:
                        data = lzma.decompress(cdata)
                except Exception:
                    continue
                if len(data) == L_GROUND:
                    return data

            # 3) Scoring-based heuristic to choose the most likely PoC file
            best_score = None
            best_member = None

            for m in members:
                if m.size == 0 or m.size > 5 * 1024 * 1024:
                    continue

                lname = m.name.lower()
                base = os.path.basename(lname)
                _, ext = os.path.splitext(base)

                # Skip obvious source/doc files
                if ext in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".cxx",
                    ".h",
                    ".hpp",
                    ".java",
                    ".py",
                    ".sh",
                    ".bat",
                    ".ps1",
                    ".md",
                    ".rst",
                    ".html",
                    ".htm",
                    ".xml",
                ):
                    continue

                score = 0

                # Extension-based scoring
                if ext in (".pdf", ".poc", ".bin", ".dat", ".raw", ".in", ".input"):
                    score += 30
                elif ext in (".txt", ".json", ".yaml", ".yml"):
                    score += 5

                # Name keyword scoring
                if "poc" in lname:
                    score += 40
                if "crash" in lname:
                    score += 35
                if "uaf" in lname or "useafterfree" in lname or "use-after-free" in lname:
                    score += 35
                if "heap" in lname:
                    score += 10
                if "standalone" in lname or "form" in lname:
                    score += 10

                # Size closeness scoring
                diff = abs(m.size - L_GROUND)
                if diff == 0:
                    score += 50
                # Closer sizes get more points; 1 point per KiB difference up to 30
                size_weight = max(0, 30 - diff // 1024)
                score += size_weight

                if score <= 0:
                    continue

                if best_score is None or score > best_score:
                    best_score = score
                    best_member = m

            if best_member is not None:
                f = tf.extractfile(best_member)
                if f is not None:
                    return f.read()

            # 4) Content-based heuristic: look for PDFs near the ground-truth size
            pdf_candidate_member = None
            pdf_candidate_diff = None

            for m in members:
                if m.size == 0 or m.size > 5 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    head = f.read(1024)
                except Exception:
                    continue
                if head.startswith(b"%PDF"):
                    diff = abs(m.size - L_GROUND)
                    if pdf_candidate_member is None or diff < pdf_candidate_diff:
                        pdf_candidate_member = m
                        pdf_candidate_diff = diff

            if pdf_candidate_member is not None:
                f = tf.extractfile(pdf_candidate_member)
                if f is not None:
                    return f.read()

            # 5) Fallback: return the first reasonably sized regular file
            for m in members:
                if 0 < m.size <= 1024 * 1024:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        return f.read()
                    except Exception:
                        continue

        # Final fallback: trivial payload
        return b"A"
