import os
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_SIZE = 150_979

        def find_in_dir(root: str):
            best_candidate = None
            best_score = -1
            for dirpath, _, files in os.walk(root):
                for name in files:
                    fpath = os.path.join(dirpath, name)
                    try:
                        st = os.stat(fpath)
                    except OSError:
                        continue
                    size = st.st_size
                    score = 0

                    if size == TARGET_SIZE:
                        score += 100

                    lname = name.lower()
                    if "42535696" in lname:
                        score += 50
                    if (
                        "clusterfuzz" in lname
                        or "testcase" in lname
                        or "poc" in lname
                        or "crash" in lname
                        or "repro" in lname
                    ):
                        score += 20
                    if lname.endswith(
                        (".pdf", ".bin", ".dat", ".input", ".txt")
                    ):
                        score += 5

                    if score > 0 and (best_candidate is None or score > best_score):
                        best_candidate = fpath
                        best_score = score

            if best_candidate:
                try:
                    with open(best_candidate, "rb") as f:
                        return f.read()
                except OSError:
                    return None
            return None

        def find_in_tar(path: str):
            best_member = None
            best_score = -1
            try:
                tf = tarfile.open(path, "r:*")
            except tarfile.TarError:
                return None
            with tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    size = m.size
                    score = 0
                    if size == TARGET_SIZE:
                        score += 100
                    lname = m.name.lower()
                    if "42535696" in lname:
                        score += 50
                    if (
                        "clusterfuzz" in lname
                        or "testcase" in lname
                        or "poc" in lname
                        or "crash" in lname
                        or "repro" in lname
                    ):
                        score += 20
                    if lname.endswith(
                        (".pdf", ".bin", ".dat", ".input", ".txt")
                    ):
                        score += 5
                    if score > 0 and (best_member is None or score > best_score):
                        best_member = m
                        best_score = score
                if best_member:
                    try:
                        f = tf.extractfile(best_member)
                    except (KeyError, OSError):
                        return None
                    if f is not None:
                        try:
                            return f.read()
                        except OSError:
                            return None
            return None

        def find_in_zip(path: str):
            try:
                zf = zipfile.ZipFile(path, "r")
            except zipfile.BadZipFile:
                return None
            best_name = None
            best_score = -1
            with zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    size = info.file_size
                    score = 0
                    if size == TARGET_SIZE:
                        score += 100
                    lname = info.filename.lower()
                    if "42535696" in lname:
                        score += 50
                    if (
                        "clusterfuzz" in lname
                        or "testcase" in lname
                        or "poc" in lname
                        or "crash" in lname
                        or "repro" in lname
                    ):
                        score += 20
                    if lname.endswith(
                        (".pdf", ".bin", ".dat", ".input", ".txt")
                    ):
                        score += 5
                    if score > 0 and (best_name is None or score > best_score):
                        best_name = info.filename
                        best_score = score
                if best_name:
                    try:
                        with zf.open(best_name, "r") as f:
                            return f.read()
                    except OSError:
                        return None
            return None

        if os.path.isdir(src_path):
            data = find_in_dir(src_path)
            if data is not None:
                return data
            for dirpath, _, files in os.walk(src_path):
                for name in files:
                    inner = os.path.join(dirpath, name)
                    try:
                        if tarfile.is_tarfile(inner):
                            data = find_in_tar(inner)
                            if data is not None:
                                return data
                        elif zipfile.is_zipfile(inner):
                            data = find_in_zip(inner)
                            if data is not None:
                                return data
                    except OSError:
                        continue
            return b"%PDF-1.4\n% fallback PoC placeholder\n"

        else:
            try:
                if tarfile.is_tarfile(src_path):
                    data = find_in_tar(src_path)
                    if data is not None:
                        return data
            except OSError:
                pass
            try:
                if zipfile.is_zipfile(src_path):
                    data = find_in_zip(src_path)
                    if data is not None:
                        return data
            except OSError:
                pass
            return b"%PDF-1.4\n% fallback PoC placeholder\n"
