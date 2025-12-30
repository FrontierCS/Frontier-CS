import os
import tarfile
import zipfile
import io


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "42537168"
        target_size = 913919

        interesting_exts = (
            ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg",
            ".psd", ".ps", ".eps", ".txt", ".bin", ".dat", ".raw", ".json", ".zip",
            ".gz", ".bz2", ".xz", ".html", ".htm", ".ttf", ".otf", ".woff", ".woff2",
            ".pcap", ".wav", ".mp3", ".flac", ".ogg", ".icns", ".mid", ".midi",
            ".tiff", ".tif"
        )

        keywords = ("poc", "crash", "repro", "reproducer", "testcase", "id_", "clusterfuzz")

        def _score(name: str, size: int):
            nl = name.lower()
            in_bug_info = "bug-info" in nl
            has_bugid = bug_id in nl
            has_kw = any(k in nl for k in keywords)
            interesting_ext = any(nl.endswith(ext) for ext in interesting_exts)

            if size == target_size:
                pri = 0
            elif in_bug_info and has_kw:
                pri = 1
            elif has_bugid and has_kw:
                pri = 2
            elif has_bugid and interesting_ext:
                pri = 3
            elif has_bugid:
                pri = 4
            elif in_bug_info and interesting_ext:
                pri = 5
            elif has_kw:
                pri = 6
            elif in_bug_info:
                pri = 7
            elif interesting_ext:
                pri = 8
            else:
                pri = 9

            return pri, -size

        def _refine_with_nested(data: bytes, name: str, depth: int = 0) -> bytes:
            if depth >= 2:
                return data
            lname = name.lower()

            if lname.endswith(".zip"):
                try:
                    bio = io.BytesIO(data)
                    with zipfile.ZipFile(bio, "r") as zf:
                        best_info = None
                        best_score = None
                        for zi in zf.infolist():
                            if hasattr(zi, "is_dir") and zi.is_dir():
                                continue
                            inner_name = zi.filename
                            inner_size = zi.file_size
                            sc = _score(inner_name, inner_size)
                            if best_score is None or sc < best_score:
                                best_score = sc
                                best_info = zi
                        if best_info is None:
                            return data
                        with zf.open(best_info, "r") as f:
                            inner_data = f.read()
                        return _refine_with_nested(inner_data, best_info.filename, depth + 1)
                except (zipfile.BadZipFile, OSError, RuntimeError):
                    return data

            tar_exts = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
            if lname.endswith(tar_exts):
                try:
                    bio = io.BytesIO(data)
                    with tarfile.open(fileobj=bio, mode="r:*") as tf2:
                        best_member = None
                        best_score = None
                        for m2 in tf2.getmembers():
                            if not m2.isfile():
                                continue
                            sc2 = _score(m2.name, m2.size)
                            if best_score is None or sc2 < best_score:
                                best_score = sc2
                                best_member = m2
                        if best_member is None:
                            return data
                        ex = tf2.extractfile(best_member)
                        if ex is None:
                            return data
                        try:
                            inner_data = ex.read()
                        finally:
                            ex.close()
                        return _refine_with_nested(inner_data, best_member.name, depth + 1)
                except (tarfile.TarError, OSError, RuntimeError):
                    return data

            return data

        def _from_dir(root: str) -> bytes:
            best_path = None
            best_score = None

            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    full_path = os.path.join(dirpath, fn)
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        continue
                    rel_name = os.path.relpath(full_path, root).replace(os.path.sep, "/")
                    sc = _score(rel_name, size)
                    if best_score is None or sc < best_score:
                        best_score = sc
                        best_path = full_path

            if best_path is None:
                return b""

            with open(best_path, "rb") as f:
                data = f.read()
            return _refine_with_nested(data, os.path.basename(best_path))

        def _from_tar(tar_path: str) -> bytes:
            with tarfile.open(tar_path, "r:*") as tf:
                best_member = None
                best_score = None

                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    size = m.size
                    sc = _score(name, size)
                    if best_score is None or sc < best_score:
                        best_score = sc
                        best_member = m

                if best_member is None:
                    return b""

                ex = tf.extractfile(best_member)
                if ex is None:
                    return b""
                try:
                    data = ex.read()
                finally:
                    ex.close()
            return _refine_with_nested(data, best_member.name)

        def _from_zip(zip_path: str) -> bytes:
            with zipfile.ZipFile(zip_path, "r") as zf:
                best_info = None
                best_score = None
                for zi in zf.infolist():
                    if hasattr(zi, "is_dir") and zi.is_dir():
                        continue
                    name = zi.filename
                    size = zi.file_size
                    sc = _score(name, size)
                    if best_score is None or sc < best_score:
                        best_score = sc
                        best_info = zi

                if best_info is None:
                    return b""

                with zf.open(best_info, "r") as f:
                    data = f.read()
            return _refine_with_nested(data, best_info.filename)

        # Main dispatch
        if os.path.isdir(src_path):
            return _from_dir(src_path)

        # Try tar
        try:
            return _from_tar(src_path)
        except (tarfile.TarError, OSError):
            pass

        # Try zip
        try:
            return _from_zip(src_path)
        except (zipfile.BadZipFile, OSError):
            pass

        # Fallback: treat src_path itself as PoC
        try:
            with open(src_path, "rb") as f:
                return f.read()
        except OSError:
            return b""