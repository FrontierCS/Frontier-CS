import os
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a generic payload with extended-like TLV structure, total 844 bytes.
        # Layout (heuristic):
        # [0]: Outer TLV type (arbitrary non-zero)
        # [1]: Marker for extended length (0xFF as placeholder)
        # [2:4]: 2-byte big-endian length (840)
        # [4:]: Payload of 840 bytes including an inner TLV with a long length to simulate overflow.
        total_len = 844
        outer_value_len = total_len - 4  # assume 1 byte type + 3 bytes "extended length" header
        # Outer header
        outer_type = 0xA1  # arbitrary non-zero type
        extended_marker = 0xFF
        outer_len_be = struct.pack(">H", outer_value_len)
        header = bytes([outer_type, extended_marker]) + outer_len_be

        # Inner TLV: type + extended len + large value
        inner_type = 0xB2  # arbitrary non-zero type
        inner_extended_marker = 0xFF
        # Inner value length: make it large but fit within outer_value_len minus inner header (3 bytes)
        inner_value_len = outer_value_len - 3
        if inner_value_len < 0:
            inner_value_len = 0
        inner_len_be = struct.pack(">H", inner_value_len)
        # Inner value: pattern of bytes to avoid being all zeros
        random.seed(0x20775)
        inner_value = bytearray(inner_value_len)
        for i in range(inner_value_len):
            inner_value[i] = (i * 7 + 13) & 0xFF
        # Try to introduce plausible sub-structure headers within inner value to resemble nested TLVs
        # Insert a few mock TLV-like segments inside the value
        def put_tlv(buf, off, t, vlen):
            if off + 3 > len(buf):
                return off
            buf[off] = t & 0xFF
            buf[off + 1] = 0xFF  # extended marker
            if off + 3 > len(buf):
                return off + 3
            v = min(vlen, len(buf) - (off + 3))
            buf[off + 2] = (v >> 8) & 0xFF
            if off + 3 <= len(buf):
                if off + 3 + v <= len(buf):
                    buf[off + 3:off + 3 + v] = bytes([(t + i) & 0xFF for i in range(v)])
            return off + 3 + v

        pos = 0
        pos = put_tlv(inner_value, pos, 0x11, 128)
        pos = put_tlv(inner_value, pos, 0x22, 256)
        pos = put_tlv(inner_value, pos, 0x33, 64)
        pos = put_tlv(inner_value, pos, 0x44, 64)
        # Fill the rest deterministically
        for i in range(pos, len(inner_value)):
            inner_value[i] = (0xC3 + i * 3) & 0xFF

        inner = bytes([inner_type, inner_extended_marker]) + inner_len_be + bytes(inner_value)

        payload = header + inner
        # Ensure exact length
        if len(payload) < total_len:
            payload += b'\x00' * (total_len - len(payload))
        elif len(payload) > total_len:
            payload = payload[:total_len]

        return payload