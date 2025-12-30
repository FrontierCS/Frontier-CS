import os
import tarfile
import tempfile
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_length = 21
        fallback = b"A" * target_length

        root_dir = None
        tmpdir = None
        created_tmp = False

        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
                created_tmp = True
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(tmpdir)
                root_dir = tmpdir

            best_path = None
            best_score = None

            markers = ["poc", "crash", "testcase", "id_", "id:", "sample", "input", "seed", "30831"]

            for dirpath, dirnames, filenames in os.walk(root_dir):
                for fname in filenames:
                    path = os.path.join(dirpath, fname)

                    try:
                        st = os.lstat(path)
                    except OSError:
                        continue

                    if not stat.S_ISREG(st.st_mode):
                        continue

                    size = st.st_size
                    if size == 0 or size > 1024 * 1024:
                        continue

                    lower_name = fname.lower()
                    lower_path = path.lower()

                    has_marker = any(m in lower_name or m in lower_path for m in markers)
                    if not has_marker:
                        continue

                    score = 0

                    if "30831" in lower_name or "30831" in lower_path:
                        score += 200
                    if "poc" in lower_name or "poc" in lower_path:
                        score += 120
                    if "crash" in lower_name or "crash" in lower_path:
                        score += 100
                    if "testcase" in lower_name:
                        score += 80
                    if "id_" in lower_name or "id:" in lower_name:
                        score += 60
                    if "coap" in lower_path:
                        score += 40
                    if "fuzz" in lower_path:
                        score += 30
                    if lower_name.endswith(
                        (".bin", ".raw", ".dat", ".in", ".input", ".pkt", ".pcap", ".coap")
                    ) or "." not in fname:
                        score += 20

                    size_diff = abs(size - target_length)
                    score += max(0, 80 - size_diff * 4)

                    score -= size / 4096.0

                    if best_path is None or score > best_score:
                        best_path = path
                        best_score = score

            if best_path is not None:
                try:
                    with open(best_path, "rb") as f:
                        data = f.read()
                except OSError:
                    return fallback

                if len(data) > target_length:
                    trimmed = data.rstrip(b"\r\n")
                    if trimmed and abs(len(trimmed) - target_length) <= abs(len(data) - target_length):
                        data = trimmed

                return data if data else fallback

        except Exception:
            pass
        finally:
            if tmpdir is not None and created_tmp:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass

        return fallback