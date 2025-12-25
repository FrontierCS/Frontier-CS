import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        def ipv4_checksum(hdr: bytes) -> int:
            if len(hdr) % 2:
                hdr += b"\x00"
            s = 0
            for i in range(0, len(hdr), 2):
                s += (hdr[i] << 8) | hdr[i + 1]
            while s >> 16:
                s = (s & 0xFFFF) + (s >> 16)
            return (~s) & 0xFFFF

        payload = bytes([0x00, 0x10, 0x00, 0x00, 0x00])  # 5 bytes
        src_ip = b"\x01\x02\x03\x04"
        dst_ip = b"\x05\x06\x07\x08"

        total_len = 20 + 8 + len(payload)
        ver_ihl = 0x45
        tos = 0x00
        identification = 0x0000
        flags_frag = 0x0000
        ttl = 0x40
        proto = 17  # UDP
        checksum = 0x0000

        ip_hdr_wo_csum = struct.pack(
            "!BBHHHBBH4s4s",
            ver_ihl,
            tos,
            total_len,
            identification,
            flags_frag,
            ttl,
            proto,
            checksum,
            src_ip,
            dst_ip,
        )
        csum = ipv4_checksum(ip_hdr_wo_csum)
        ip_hdr = struct.pack(
            "!BBHHHBBH4s4s",
            ver_ihl,
            tos,
            total_len,
            identification,
            flags_frag,
            ttl,
            proto,
            csum,
            src_ip,
            dst_ip,
        )

        src_port = 5246
        dst_port = 5247
        udp_len = 8 + len(payload)
        udp_checksum = 0x0000
        udp_hdr = struct.pack("!HHHH", src_port, dst_port, udp_len, udp_checksum)

        return ip_hdr + udp_hdr + payload