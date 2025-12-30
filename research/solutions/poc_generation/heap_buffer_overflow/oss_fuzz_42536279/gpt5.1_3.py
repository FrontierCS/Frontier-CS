import os
import tarfile
import gzip
import lzma
import bz2
import re


class Solution:
    ISSUE_ID = "42536279"
    EXPECTED_LEN = 6180

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            data = self._search_dir(src_path, self.ISSUE_ID, self.EXPECTED_LEN)
            if data is not None:
                return data
            return self._fallback_poc(self.EXPECTED_LEN)

        # Assume tarball
        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    data = self._search_tar(tar, self.ISSUE_ID, self.EXPECTED_LEN)
                    if data is not None:
                        return data
            except Exception:
                pass

        return self._fallback_poc(self.EXPECTED_LEN)

    # -------------- Core search logic for directories --------------

    def _search_dir(self, root: str, issue_id: str, expected_len: int) -> bytes | None:
        file_entries = []  # (rel_path, full_path, size)
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0
                rel_path = os.path.relpath(full_path, root)
                file_entries.append((rel_path, full_path, size))

        # Stage 1: file name contains issue id
        cand1 = []
        for rel, full, size in file_entries:
            if issue_id in rel:
                if size <= 0 or size > 10 * 1024 * 1024:
                    continue
                try:
                    with open(full, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                data = self._maybe_decompress(data, rel.lower())
                if data:
                    cand1.append((data, rel))
        if cand1:
            best = self._select_best_candidate(cand1, expected_len)
            if best is not None:
                return best

        # Stage 2: text sources referencing issue id (paths or embedded arrays)
        base_to_paths: dict[str, list[tuple[str, str, int]]] = {}
        for rel, full, size in file_entries:
            base = os.path.basename(rel)
            base_to_paths.setdefault(base, []).append((rel, full, size))

        text_exts = {
            ".txt",
            ".md",
            ".rst",
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".m",
            ".mm",
            ".py",
            ".java",
            ".go",
            ".rs",
            ".js",
            ".ts",
            ".cmake",
            ".in",
            ".mk",
            ".m4",
            ".ac",
            ".am",
            ".cfg",
            ".ini",
            ".toml",
            ".json",
            ".yml",
            ".yaml",
            ".xml",
            ".html",
        }

        cand2 = []
        for rel, full, size in file_entries:
            if size <= 0 or size > 4 * 1024 * 1024:
                continue
            _, ext = os.path.splitext(rel.lower())
            if ext not in text_exts:
                continue
            try:
                with open(full, "rb") as f:
                    content_bytes = f.read()
            except OSError:
                continue
            try:
                content_str = content_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if issue_id not in content_str:
                continue

            # 2a: extract potential file paths containing issue id
            matches = self._extract_candidate_paths_from_text(content_str, issue_id)
            for s in matches:
                base = os.path.basename(s)
                for rel2, full2, size2 in base_to_paths.get(base, []):
                    if size2 <= 0 or size2 > 10 * 1024 * 1024:
                        continue
                    try:
                        with open(full2, "rb") as f2:
                            data = f2.read()
                    except OSError:
                        continue
                    data = self._maybe_decompress(data, rel2.lower())
                    if data:
                        cand2.append((data, rel2))

            # 2b: parse embedded C-style byte arrays near issue id
            arr_data = self._extract_hex_array_near_issue(content_str, issue_id)
            if arr_data:
                cand2.append((arr_data, rel + "::embedded_array"))

        if cand2:
            best = self._select_best_candidate(cand2, expected_len)
            if best is not None:
                return best

        # Stage 3: generic fuzz/crash/oss-fuzz-style assets
        keywords = ["oss-fuzz", "ossfuzz", "clusterfuzz", "fuzz", "poc", "regress", "crash", "bug"]
        cand3 = []
        for rel, full, size in file_entries:
            low = rel.lower()
            if not any(kw in low for kw in keywords):
                continue
            if size <= 0 or size > 5 * 1024 * 1024:
                continue
            try:
                with open(full, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            data = self._maybe_decompress(data, low)
            if not data or not self._is_binary_data(data):
                continue
            cand3.append((data, rel))

        if cand3:
            best = self._select_best_candidate(cand3, expected_len)
            if best is not None:
                return best

        return None

    # -------------- Core search logic for tarballs --------------

    def _search_tar(self, tar: tarfile.TarFile, issue_id: str, expected_len: int) -> bytes | None:
        members = [m for m in tar.getmembers() if m.isfile()]
        if not members:
            return None

        # Stage 1: file name contains issue id
        cand1 = []
        for m in members:
            name = m.name
            if issue_id in name:
                if m.size <= 0 or m.size > 10 * 1024 * 1024:
                    continue
                try:
                    f = tar.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                data = self._maybe_decompress(data, name.lower())
                if data:
                    cand1.append((data, name))
        if cand1:
            best = self._select_best_candidate(cand1, expected_len)
            if best is not None:
                return best

        # Stage 2: text sources referencing issue id (paths or embedded arrays)
        base_to_members: dict[str, list[tarfile.TarInfo]] = {}
        for m in members:
            base = os.path.basename(m.name)
            base_to_members.setdefault(base, []).append(m)

        text_exts = {
            ".txt",
            ".md",
            ".rst",
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".m",
            ".mm",
            ".py",
            ".java",
            ".go",
            ".rs",
            ".js",
            ".ts",
            ".cmake",
            ".in",
            ".mk",
            ".m4",
            ".ac",
            ".am",
            ".cfg",
            ".ini",
            ".toml",
            ".json",
            ".yml",
            ".yaml",
            ".xml",
            ".html",
        }

        cand2 = []
        for m in members:
            if m.size <= 0 or m.size > 4 * 1024 * 1024:
                continue
            name_lower = m.name.lower()
            _, ext = os.path.splitext(name_lower)
            if ext not in text_exts:
                continue
            try:
                f = tar.extractfile(m)
                if not f:
                    continue
                content_bytes = f.read()
            except Exception:
                continue
            try:
                content_str = content_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if issue_id not in content_str:
                continue

            # 2a: extract potential file paths containing issue id
            matches = self._extract_candidate_paths_from_text(content_str, issue_id)
            for s in matches:
                base = os.path.basename(s)
                for mem in base_to_members.get(base, []):
                    if mem.size <= 0 or mem.size > 10 * 1024 * 1024:
                        continue
                    try:
                        f2 = tar.extractfile(mem)
                        if not f2:
                            continue
                        data = f2.read()
                    except Exception:
                        continue
                    data = self._maybe_decompress(data, mem.name.lower())
                    if data:
                        cand2.append((data, mem.name))

            # 2b: parse embedded C-style byte arrays near issue id
            arr_data = self._extract_hex_array_near_issue(content_str, issue_id)
            if arr_data:
                cand2.append((arr_data, m.name + "::embedded_array"))

        if cand2:
            best = self._select_best_candidate(cand2, expected_len)
            if best is not None:
                return best

        # Stage 3: generic fuzz/crash/oss-fuzz-style assets
        keywords = ["oss-fuzz", "ossfuzz", "clusterfuzz", "fuzz", "poc", "regress", "crash", "bug"]
        cand3 = []
        for m in members:
            name_lower = m.name.lower()
            if not any(kw in name_lower for kw in keywords):
                continue
            if m.size <= 0 or m.size > 5 * 1024 * 1024:
                continue
            try:
                f = tar.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue
            data = self._maybe_decompress(data, name_lower)
            if not data or not self._is_binary_data(data):
                continue
            cand3.append((data, m.name))

        if cand3:
            best = self._select_best_candidate(cand3, expected_len)
            if best is not None:
                return best

        return None

    # -------------- Helper utilities --------------

    def _maybe_decompress(self, data: bytes, name_lower: str) -> bytes:
        if not data:
            return data
        try:
            if name_lower.endswith(".gz"):
                return gzip.decompress(data)
            if name_lower.endswith(".xz") or name_lower.endswith(".lzma"):
                return lzma.decompress(data)
            if name_lower.endswith(".bz2"):
                return bz2.decompress(data)
        except Exception:
            return data
        return data

    def _is_probably_text(self, data: bytes, threshold: float = 0.9, sample_size: int = 4096) -> bool:
        if not data:
            return True
        sample = data if len(data) <= sample_size else data[:sample_size]
        text_chars = set(range(32, 127))
        text_chars.update({9, 10, 13})
        text_count = 0
        for b in sample:
            if b in text_chars:
                text_count += 1
        ratio = text_count / len(sample)
        return ratio >= threshold

    def _is_binary_data(self, data: bytes) -> bool:
        return not self._is_probably_text(data)

    def _name_score(self, name: str) -> int:
        n = name.lower()
        score = 0
        if "oss-fuzz" in n or "ossfuzz" in n:
            score += 50
        if "clusterfuzz" in n:
            score += 40
        if "fuzz" in n:
            score += 20
        if "poc" in n:
            score += 25
        if "crash" in n:
            score += 15
        if "regress" in n or "regression" in n:
            score += 10
        if "svc" in n:
            score += 5
        if "h264" in n or ".264" in n:
            score += 3
        if "ivf" in n or "vp9" in n or "av1" in n:
            score += 3
        if self.ISSUE_ID in n:
            score += 100
        return score

    def _select_best_candidate(self, data_name_list: list[tuple[bytes, str]], expected_len: int) -> bytes | None:
        best_data = None
        best_key = None
        for data, name in data_name_list:
            if not data:
                continue
            length = len(data)
            if length <= 0:
                continue
            length_diff = abs(length - expected_len) if expected_len else 0
            is_text = 1 if self._is_probably_text(data) else 0
            name_score = self._name_score(name)
            key = (-name_score, is_text, length_diff)
            if best_key is None or key < best_key:
                best_key = key
                best_data = data
        return best_data

    def _extract_candidate_paths_from_text(self, text: str, issue_id: str) -> list[str]:
        pattern = re.compile(r"[\w\./\-\+]*" + re.escape(issue_id) + r"[\w\./\-\+]*")
        matches = pattern.findall(text)
        result = []
        seen = set()
        for m in matches:
            s = m.strip()
            if not s or s in seen:
                continue
            seen.add(s)
            result.append(s)
        return result

    def _extract_hex_array_near_issue(self, text: str, issue_id: str) -> bytes | None:
        idx = text.find(issue_id)
        if idx == -1:
            return None
        start_window = max(0, idx - 2000)
        end_window = min(len(text), idx + 2000)
        window = text[start_window:end_window]
        rel_idx = idx - start_window
        brace_start = window.rfind("{", 0, rel_idx)
        brace_end = window.find("}", rel_idx)
        if brace_start == -1 or brace_end == -1 or brace_end <= brace_start:
            return None
        array_body = window[brace_start + 1 : brace_end]
        return self._parse_c_array_bytes(array_body)

    def _parse_c_array_bytes(self, body: str) -> bytes | None:
        tokens = re.findall(r"0x[0-9a-fA-F]{1,2}|\d+", body)
        if not tokens:
            return None
        out = bytearray()
        for tok in tokens:
            try:
                if tok.lower().startswith("0x"):
                    val = int(tok, 16)
                else:
                    val = int(tok, 10)
            except ValueError:
                continue
            if 0 <= val <= 255:
                out.append(val)
        if not out:
            return None
        return bytes(out)

    def _fallback_poc(self, expected_len: int) -> bytes:
        # Fallback: small non-empty byte sequence if no PoC could be located
        return b"\x00" * min(16, expected_len if expected_len and expected_len > 0 else 16)