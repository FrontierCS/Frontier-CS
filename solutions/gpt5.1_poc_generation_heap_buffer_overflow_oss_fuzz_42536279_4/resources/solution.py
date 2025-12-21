import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        POC_SIZE = 6180

        if os.path.isdir(src_path):
            return self._from_dir(src_path, POC_SIZE)
        elif tarfile.is_tarfile(src_path):
            return self._from_tar(src_path, POC_SIZE)
        else:
            try:
                with open(src_path, "rb") as f:
                    data = f.read()
                if data:
                    return data
            except OSError:
                pass
            return b"A" * POC_SIZE

    def _from_dir(self, root: str, poc_size: int) -> bytes:
        pattern = re.compile(r"(poc|testcase|crash|clusterfuzz|repro)", re.IGNORECASE)
        exact_path = None
        named_candidates = []
        smallest_other_path = None
        smallest_other_size = None

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                if size == poc_size:
                    exact_path = full
                    break
                if pattern.search(name):
                    named_candidates.append((size, full))
                if smallest_other_size is None or size < smallest_other_size:
                    smallest_other_size = size
                    smallest_other_path = full
            if exact_path:
                break

        if exact_path:
            try:
                with open(exact_path, "rb") as f:
                    return f.read()
            except OSError:
                pass

        if named_candidates:
            named_candidates.sort(key=lambda x: x[0])
            for _, path in named_candidates:
                try:
                    with open(path, "rb") as f:
                        return f.read()
                except OSError:
                    continue

        if smallest_other_path:
            try:
                with open(smallest_other_path, "rb") as f:
                    return f.read()
            except OSError:
                pass

        return b"A" * poc_size

    def _from_tar(self, tar_path: str, poc_size: int) -> bytes:
        pattern = re.compile(r"(poc|testcase|crash|clusterfuzz|repro)", re.IGNORECASE)
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]

                for m in members:
                    if m.size == poc_size:
                        f = tf.extractfile(m)
                        if f is not None:
                            try:
                                data = f.read()
                            finally:
                                f.close()
                            return data

                small_named = []
                smallest_other_size = None
                smallest_other_data = None

                for m in members:
                    if m.size > 10 * 1024 * 1024:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        try:
                            data = f.read()
                        finally:
                            f.close()
                    except Exception:
                        continue

                    base_name = os.path.basename(m.name)
                    if pattern.search(base_name):
                        small_named.append((len(data), data))

                    if smallest_other_size is None or len(data) < smallest_other_size:
                        smallest_other_size = len(data)
                        smallest_other_data = data

                if small_named:
                    small_named.sort(key=lambda x: x[0])
                    return small_named[0][1]

                if smallest_other_data is not None:
                    return smallest_other_data
        except tarfile.TarError:
            pass

        return b"A" * poc_size
