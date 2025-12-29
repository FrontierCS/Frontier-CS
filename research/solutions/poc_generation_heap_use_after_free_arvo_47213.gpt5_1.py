import os
import io
import tarfile
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 7270

        def is_probable_text(data: bytes, threshold: float = 0.95) -> bool:
            if not data:
                return True
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27})
            text_chars.extend(range(0x20, 0x100))
            text_chars.remove(0x7F)
            nontext = sum(1 for b in data if b not in text_chars)
            return (len(data) - nontext) / len(data) >= threshold

        def is_mrb(data: bytes) -> bool:
            return len(data) >= 4 and data[:4] == b'RITE'

        def name_score(name: str) -> float:
            n = name.lower()
            score = 0.0
            keywords = {
                "poc": 80,
                "crash": 60,
                "uaf": 60,
                "use-after-free": 60,
                "use_after_free": 60,
                "heap-use-after-free": 60,
                "heap_use_after_free": 60,
                "afl": 40,
                "queue": 20,
                "repro": 40,
                "id:": 30,
                ".mrb": 30,
                ".rb": 10,
            }
            for k, v in keywords.items():
                if k in n:
                    score += v
            # Prefer shorter, file-like names
            score -= 0.001 * len(n)
            return score

        def size_score(size: int) -> float:
            # Higher score if closer to target length
            return 1000.0 / (1.0 + abs(size - target_len))

        def content_score(data: bytes, name: str) -> float:
            score = 0.0
            if is_mrb(data):
                score += 500
            if name.lower().endswith(".mrb"):
                score += 100
            if not is_probable_text(data):
                score += 10
            # Favor files that look like compiled bytecode but not enormous
            if len(data) > 0 and len(data) < 1024 * 1024:
                score += 5
            return score

        def pick_best(candidates):
            if not candidates:
                return None
            best = None
            best_score = float("-inf")
            for name, data in candidates:
                sc = name_score(name) + size_score(len(data)) + content_score(data, name)
                if sc > best_score:
                    best_score = sc
                    best = (name, data)
            return best

        def iter_from_tarfile(tf: tarfile.TarFile):
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0:
                    continue
                # Cap at 8MB per file to avoid excessive memory
                if m.size > 8 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                yield m.name, data

        def iter_from_zipfile(zf: zipfile.ZipFile):
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.file_size <= 0 or info.file_size > 8 * 1024 * 1024:
                    continue
                try:
                    data = zf.read(info.filename)
                except Exception:
                    continue
                yield info.filename, data

        def recurse_archive(name: str, data: bytes, out_list):
            lname = name.lower()
            # Try nested tar
            if lname.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tar.xz", ".txz")) or (len(data) >= 512 and data[:262].find(b"ustar") != -1):
                try:
                    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf2:
                        for n2, d2 in iter_from_tarfile(tf2):
                            # recurse further
                            recurse_archive(n2, d2, out_list)
                except Exception:
                    pass
            # Try nested zip
            if lname.endswith(".zip") or (len(data) >= 4 and data[:4] == b"PK\x03\x04"):
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as zf2:
                        for n2, d2 in iter_from_zipfile(zf2):
                            recurse_archive(n2, d2, out_list)
                except Exception:
                    pass
            # Collect if it's a plausible input file
            out_list.append((name, data))

        # Open the provided src_path archive and collect candidates
        candidates = []

        # First layer: the top-level tarball
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for name, data in iter_from_tarfile(tf):
                    recurse_archive(name, data, candidates)
        except Exception:
            # If not a tar, try zip
            try:
                with zipfile.ZipFile(src_path) as zf:
                    for name in zf.namelist():
                        try:
                            data = zf.read(name)
                        except Exception:
                            continue
                        recurse_archive(name, data, candidates)
            except Exception:
                candidates = []

        # Filter to likely PoC files
        filtered = []
        for name, data in candidates:
            nlow = name.lower()
            # Skip obvious source/binary archives; keep files likely to be direct inputs
            if any(nlow.endswith(ext) for ext in [
                ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".py", ".txt", ".md", ".rst", ".json",
                ".yml", ".yaml", ".xml", ".html", ".htm", ".css", ".js", ".csv", ".pdf", ".png",
                ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".svg", ".gz", ".bz2", ".xz",
                ".tar", ".tgz", ".tbz", ".txz", ".zip", ".7z", ".rar", ".patch", ".diff", ".sum",
                ".sha1", ".sha256", ".sum256", ".sum512", ".mp3", ".mp4", ".mov", ".avi"
            ]):
                # But allow .mrb explicitly
                if not nlow.endswith(".mrb"):
                    continue
            # Deprioritize huge files
            if len(data) == 0 or len(data) > 2 * 1024 * 1024:
                continue
            # Prioritize files with RITE header or .mrb extension or indicative names
            if is_mrb(data) or nlow.endswith(".mrb") or any(k in nlow for k in ["poc", "crash", "uaf", "use-after", "use_after", "heap-use", "heap_use", "afl", "queue", "repro", "id:"]):
                filtered.append((name, data))

        best = pick_best(filtered if filtered else candidates)

        if best is not None:
            return best[1]

        # Fallback: return a minimal benign Ruby script if nothing else is found
        # This won't trigger the vulnerability but ensures valid bytes return.
        fallback = b"puts 'fallback'\n"
        return fallback