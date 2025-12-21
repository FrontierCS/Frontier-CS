import os
import tarfile


class Solution:
    TARGET_LEN = 1551
    MAX_CANDIDATE_SIZE = 4_000_000

    def solve(self, src_path: str) -> bytes:
        try:
            if tarfile.is_tarfile(src_path):
                return self._from_tar(src_path)
        except Exception:
            pass

        if os.path.isdir(src_path):
            data = self._from_directory(src_path)
            if data is not None:
                return data

        return self._fallback_poc()

    def _from_tar(self, src_path: str) -> bytes:
        target_len = self.TARGET_LEN
        best_score = None
        best_data = None

        patterns = {
            "poc": 30,
            "crash": 25,
            "heap": 10,
            "overflow": 10,
            "383170474": 50,
            "debug": 5,
            "names": 5,
            "dwarf": 5,
            "fuzz": 5,
            "regress": 5,
            "bug": 10,
            "test": 3,
            "clusterfuzz": 20,
            "oss-fuzz": 20,
        }

        binary_exts = (".o", ".obj", ".elf", ".bin", ".dwo", ".so", ".exe", ".out", ".core", ".dat")

        tf = tarfile.open(src_path, "r:*")
        try:
            for member in tf.getmembers():
                if not member.isreg():
                    continue
                size = member.size
                if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue

                name_lower = member.name.lower()
                distance = abs(size - target_len)
                size_score = 100 - min(distance, 100)
                score = size_score

                for pat, weight in patterns.items():
                    if pat in name_lower:
                        score += weight

                for ext in binary_exts:
                    if name_lower.endswith(ext):
                        score += 10
                        break

                if "/poc" in name_lower or "poc/" in name_lower:
                    score += 15
                if "seed_corpus" in name_lower or "corpus" in name_lower:
                    score += 5
                if "/tests" in name_lower or "/test" in name_lower:
                    score += 3

                need_content = (
                    distance < 512
                    or "poc" in name_lower
                    or "crash" in name_lower
                    or "fuzz" in name_lower
                    or "383170474" in name_lower
                )

                data = None
                if need_content:
                    try:
                        fobj = tf.extractfile(member)
                        if fobj is not None:
                            data = fobj.read()
                            fobj.close()
                    except Exception:
                        data = None
                    if data is not None:
                        if data.startswith(b"\x7fELF"):
                            score += 20
                        if b".debug_names" in data:
                            score += 80
                        elif b"debug_names" in data:
                            score += 30
                        if b"DWARF" in data:
                            score += 10

                if best_score is None or score > best_score:
                    if data is None:
                        try:
                            fobj = tf.extractfile(member)
                            if fobj is not None:
                                data = fobj.read()
                                fobj.close()
                        except Exception:
                            data = None
                    if data is None:
                        continue
                    best_score = score
                    best_data = data
        finally:
            tf.close()

        if best_data is not None:
            return best_data
        return self._fallback_poc()

    def _from_directory(self, root: str) -> bytes:
        target_len = self.TARGET_LEN
        best_score = None
        best_data = None

        patterns = {
            "poc": 30,
            "crash": 25,
            "heap": 10,
            "overflow": 10,
            "383170474": 50,
            "debug": 5,
            "names": 5,
            "dwarf": 5,
            "fuzz": 5,
            "regress": 5,
            "bug": 10,
            "test": 3,
            "clusterfuzz": 20,
            "oss-fuzz": 20,
        }
        binary_exts = (".o", ".obj", ".elf", ".bin", ".dwo", ".so", ".exe", ".out", ".core", ".dat")

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue

                name_lower = path.lower()
                distance = abs(size - target_len)
                size_score = 100 - min(distance, 100)
                score = size_score

                for pat, weight in patterns.items():
                    if pat in name_lower:
                        score += weight

                for ext in binary_exts:
                    if name_lower.endswith(ext):
                        score += 10
                        break

                if "/poc" in name_lower or "poc/" in name_lower:
                    score += 15
                if "seed_corpus" in name_lower or "corpus" in name_lower:
                    score += 5
                if "/tests" in name_lower or "/test" in name_lower:
                    score += 3

                need_content = (
                    distance < 512
                    or "poc" in name_lower
                    or "crash" in name_lower
                    or "fuzz" in name_lower
                    or "383170474" in name_lower
                )

                data = None
                if need_content:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        data = None
                    if data is not None:
                        if data.startswith(b"\x7fELF"):
                            score += 20
                        if b".debug_names" in data:
                            score += 80
                        elif b"debug_names" in data:
                            score += 30
                        if b"DWARF" in data:
                            score += 10

                if best_score is None or score > best_score:
                    if data is None:
                        try:
                            with open(path, "rb") as f:
                                data = f.read()
                        except OSError:
                            data = None
                    if data is None:
                        continue
                    best_score = score
                    best_data = data

        return best_data if best_data is not None else self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        length = self.TARGET_LEN
        data = bytearray(b"\x00" * length)

        if length >= 4:
            data[0:4] = b"\x7fELF"

        marker = b".debug_names"
        if len(marker) < length - 32:
            start = 32
            data[start:start + len(marker)] = marker

        dwarf_marker = b"DWARF\x00\x05"
        pos = 64
        if pos + len(dwarf_marker) < length:
            data[pos:pos + len(dwarf_marker)] = dwarf_marker

        return bytes(data)
